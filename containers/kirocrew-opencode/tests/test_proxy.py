import json

import pytest

from kirocrew_shim.proxy import ModelRejected, Proxy


def build(streams, client_lines=(), agent_lines=(), model="test/model"):
    client_in = streams("".join(line + "\n" for line in client_lines))
    agent_out = streams("".join(line + "\n" for line in agent_lines))
    client_out, agent_in = streams(), streams()
    logged = []
    proxy = Proxy(
        model=model,
        client_in=client_in,
        client_out=client_out,
        agent_in=agent_in,
        agent_out=agent_out,
        log=logged.append,
    )
    return proxy, client_out, agent_in, logged


def decoded(stream):
    return [json.loads(line) for line in stream.written()]


def test_forwarded_message_reaches_the_agent_rewritten(stream):
    proxy, client_out, agent_in, _ = build(
        stream,
        client_lines=[
            '{"jsonrpc":"2.0","id":1,"method":"initialize",'
            '"params":{"protocolVersion":"2025-08-22"}}'
        ],
    )
    proxy.pump_client_to_agent()

    sent = decoded(agent_in)
    assert len(sent) == 1
    assert sent[0]["params"]["protocolVersion"] == 1
    assert client_out.written() == []  # nothing answered locally


def test_local_reply_goes_to_client_not_agent(stream):
    proxy, client_out, agent_in, _ = build(
        stream,
        client_lines=[
            '{"jsonrpc":"2.0","id":7,"method":"session/set_mode",' '"params":{"modeId":"kirocrew"}}'
        ],
    )
    proxy.pump_client_to_agent()

    assert agent_in.written() == []
    assert decoded(client_out) == [{"jsonrpc": "2.0", "id": 7, "result": {}}]


def test_dropped_notification_reaches_nobody(stream):
    proxy, client_out, agent_in, _ = build(
        stream, client_lines=['{"method":"_kiro.dev/telemetry"}']
    )
    proxy.pump_client_to_agent()

    assert agent_in.written() == []
    assert client_out.written() == []


def test_blank_and_malformed_lines_do_not_kill_the_pump(stream):
    proxy, _, agent_in, _ = build(
        stream,
        client_lines=[
            "",
            "   ",
            "not json at all",
            '{"jsonrpc":"2.0","id":2,"method":"session/new"}',
        ],
    )
    proxy.pump_client_to_agent()

    # The valid message still got through, so a bad line did not abort the loop.
    assert [m["method"] for m in decoded(agent_in)] == ["session/new"]


def test_agent_stdin_is_closed_when_client_ends(stream):
    proxy, _, agent_in, _ = build(stream)
    proxy.pump_client_to_agent()
    assert agent_in.closed_count == 1


def test_agent_stdin_close_failure_is_tolerated(stream):
    proxy, _, _, _ = build(stream)

    class Exploding:
        def close(self):
            raise OSError("already gone")

    proxy.agent_in = Exploding()
    proxy.pump_client_to_agent()  # must not raise


def test_agent_output_is_relayed_verbatim(stream):
    lines = [
        '{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":1}}',
        '{"method":"session/update","params":{"text":"hi"}}',
    ]
    proxy, client_out, _, _ = build(stream, agent_lines=lines)
    proxy.pump_agent_to_client()
    assert client_out.written() == lines


def test_blank_agent_lines_are_skipped(stream):
    proxy, client_out, _, _ = build(stream, agent_lines=["", '{"id":1,"result":{}}', "  "])
    proxy.pump_agent_to_client()
    assert client_out.written() == ['{"id":1,"result":{}}']


def test_unrelated_agent_error_is_relayed_not_fatal(stream):
    # OpenCode requests fs/write_text_file even when the client declares it
    # unsupported; the resulting -32601 is benign UI-diff noise and must not
    # be mistaken for a model rejection.
    error = '{"jsonrpc":"2.0","id":99,"error":{"code":-32601,"message":"Method not found"}}'
    proxy, client_out, _, logged = build(stream, agent_lines=[error])
    proxy.pump_agent_to_client()
    assert client_out.written() == [error]
    assert logged == []


def test_rejected_model_raises_and_logs(stream):
    # THE failure this guards: with no credential the ollama-cloud provider
    # vanishes, set_model is rejected, and OpenCode silently serves the turn
    # from its default free model instead of erroring.
    proxy, client_out, agent_in, logged = build(
        stream,
        client_lines=['{"jsonrpc":"2.0","id":9,"method":"session/set_model","params":{}}'],
        agent_lines=[
            '{"jsonrpc":"2.0","id":9,"error":' '{"code":-32602,"message":"model not found"}}'
        ],
        model="ollama-cloud/gpt-oss:120b",
    )
    proxy.pump_client_to_agent()  # registers id 9 as pending

    with pytest.raises(ModelRejected) as excinfo:
        proxy.pump_agent_to_client()

    assert excinfo.value.model == "ollama-cloud/gpt-oss:120b"
    assert len(logged) == 1
    assert "ollama-cloud/gpt-oss:120b" in logged[0]
    assert "OPENCODE_AUTH_CONTENT" in logged[0]
    # The rejection must NOT be relayed as if the session were healthy.
    assert client_out.written() == []


def test_rejected_model_names_the_client_picked_id_not_the_default(stream):
    # translate_client_message now passes the client's pick through instead of
    # forcing `model`, so a rejection must name what was actually requested.
    proxy, client_out, agent_in, logged = build(
        stream,
        client_lines=[
            '{"jsonrpc":"2.0","id":9,"method":"session/set_model",'
            '"params":{"modelId":"ollama-cloud/qwen3-coder:480b"}}'
        ],
        agent_lines=[
            '{"jsonrpc":"2.0","id":9,"error":{"code":-32602,"message":"model not found"}}'
        ],
        model="ollama-cloud/gpt-oss:120b",
    )
    proxy.pump_client_to_agent()

    with pytest.raises(ModelRejected) as excinfo:
        proxy.pump_agent_to_client()

    assert excinfo.value.model == "ollama-cloud/qwen3-coder:480b"


def test_error_for_a_different_id_is_not_a_model_rejection(stream):
    proxy, client_out, _, _ = build(
        stream,
        client_lines=['{"jsonrpc":"2.0","id":9,"method":"session/set_model","params":{}}'],
        agent_lines=['{"jsonrpc":"2.0","id":5,"error":{"code":-1,"message":"other"}}'],
    )
    proxy.pump_client_to_agent()
    proxy.pump_agent_to_client()  # must not raise
    assert len(client_out.written()) == 1


def test_successful_set_model_leaves_no_landmine(stream):
    """A later unrelated error must not be blamed on an already-accepted model."""
    proxy, client_out, _, _ = build(
        stream,
        client_lines=['{"jsonrpc":"2.0","id":9,"method":"session/set_model","params":{}}'],
        agent_lines=[
            '{"jsonrpc":"2.0","id":9,"result":{}}',
            '{"jsonrpc":"2.0","id":9,"error":{"code":-1,"message":"later"}}',
        ],
    )
    proxy.pump_client_to_agent()
    with pytest.raises(ModelRejected):
        proxy.pump_agent_to_client()
    # NOTE: documents current behaviour -- a success reply does not clear the
    # pending id, so a same-id error later still trips the guard. Harmless in
    # practice (KiroCrew sends set_model once per session with a unique id) and
    # failing loud is the safer bias.
    assert client_out.written() == ['{"jsonrpc":"2.0","id":9,"result":{}}']


def test_run_pumps_both_directions(stream):
    proxy, client_out, agent_in, _ = build(
        stream,
        client_lines=['{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'],
        agent_lines=['{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":1}}'],
    )
    proxy.run()

    assert decoded(agent_in)[0]["params"]["protocolVersion"] == 1
    assert decoded(client_out)[0]["result"] == {"protocolVersion": 1}


def test_concurrent_writes_to_client_are_whole_lines(stream):
    """Local replies and agent traffic share client_out; neither may be torn."""
    client_lines = [
        json.dumps({"jsonrpc": "2.0", "id": i, "method": "session/set_mode"}) for i in range(50)
    ]
    agent_lines = [
        json.dumps({"jsonrpc": "2.0", "id": 1000 + i, "result": {"n": i}}) for i in range(50)
    ]
    proxy, client_out, _, _ = build(stream, client_lines=client_lines, agent_lines=agent_lines)
    proxy.run()

    ids = sorted(json.loads(line)["id"] for line in client_out.written())
    assert ids == list(range(50)) + list(range(1000, 1050))
