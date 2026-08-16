"""Tests for the deny-by-default workaround: the agent->client rawInput rewrites.

KiroCrew denies any shell tool whose command it cannot recover (hooks.py:495).
With OpenCode it could recover none, for two independent reasons -- OpenCode
reports the params as ``toolCall.rawInput`` while KiroCrew's fallback reads only
``input``/``params`` (_dispatch.py:583), and the pending ``tool_call`` OpenCode
sends first carries a cwd-only stub that KiroCrew caches and pops ahead of the
permission frame's real params. Both halves are needed; verified by replaying
these frame sequences through KiroCrew's own dispatch code.
"""

import json

from kirocrew_shim.proxy import Proxy
from kirocrew_shim.translate import rewrite_agent_message

CWD = "/home/kirocrew/work"
FULL_PARAMS = {"command": "echo hi", "cwd": CWD}
STUB_PARAMS = {"cwd": CWD}


def _permission(raw_input=FULL_PARAMS, **tool_call):
    """A session/request_permission frame shaped like OpenCode's."""
    tool_call = {"toolCallId": "tc-1", "title": "echo hi", "kind": "execute", **tool_call}
    if raw_input is not None:
        tool_call["rawInput"] = raw_input
    return {
        "jsonrpc": "2.0",
        "id": 7,
        "method": "session/request_permission",
        "params": {"sessionId": "s", "toolCall": tool_call},
    }


def _tool_call(session_update="tool_call", kind="execute", raw_input=STUB_PARAMS):
    """A session/update tool notification."""
    update = {"sessionUpdate": session_update, "toolCallId": "tc-1", "kind": kind}
    if raw_input is not None:
        update["rawInput"] = raw_input
    return {"jsonrpc": "2.0", "method": "session/update", "params": {"update": update}}


# ---------------------------------------------------------------------------
# permission frames: rawInput -> input
# ---------------------------------------------------------------------------


def test_permission_raw_input_is_copied_to_input():
    result = rewrite_agent_message(_permission())
    assert result["params"]["toolCall"]["input"] == FULL_PARAMS
    # Copied, not moved: the frame stays valid for any other reader.
    assert result["params"]["toolCall"]["rawInput"] == FULL_PARAMS


def test_permission_rewrite_does_not_mutate_the_original():
    msg = _permission()
    rewrite_agent_message(msg)
    assert "input" not in msg["params"]["toolCall"]


def test_permission_without_usable_raw_input_is_left_alone():
    for raw_input in (None, {}, "echo hi"):
        assert rewrite_agent_message(_permission(raw_input=raw_input)) is None


def test_permission_with_non_dict_tool_call_is_left_alone():
    msg = {"jsonrpc": "2.0", "method": "session/request_permission", "params": {"toolCall": None}}
    assert rewrite_agent_message(msg) is None


def test_existing_input_is_never_clobbered():
    """An agent that already speaks KiroCrew's shape owns its own params."""
    msg = _permission(input={"command": "git status"})
    assert rewrite_agent_message(msg) is None


def test_existing_params_is_never_clobbered():
    msg = _permission(params={"command": "git status"})
    assert rewrite_agent_message(msg) is None


def test_empty_existing_input_does_not_block_the_copy():
    result = rewrite_agent_message(_permission(input={}))
    assert result["params"]["toolCall"]["input"] == FULL_PARAMS


# ---------------------------------------------------------------------------
# pending shell tool_call: drop the params stub
# ---------------------------------------------------------------------------


def test_pending_shell_tool_call_loses_its_raw_input_stub():
    result = rewrite_agent_message(_tool_call())
    assert "rawInput" not in result["params"]["update"]
    assert result["params"]["update"]["toolCallId"] == "tc-1"  # rest of the frame intact


def test_stub_drop_does_not_mutate_the_original():
    msg = _tool_call()
    rewrite_agent_message(msg)
    assert msg["params"]["update"]["rawInput"] == STUB_PARAMS


def test_tool_call_update_keeps_its_raw_input():
    """The refinement carries the REAL params -- KiroCrew needs them."""
    assert rewrite_agent_message(_tool_call("tool_call_update", raw_input=FULL_PARAMS)) is None


def test_non_shell_tool_call_keeps_its_raw_input():
    """read/edit params drive the path-derived governance scopes."""
    assert rewrite_agent_message(_tool_call(kind="edit")) is None


def test_tool_call_without_raw_input_is_left_alone():
    assert rewrite_agent_message(_tool_call(raw_input=None)) is None


def test_non_dict_update_is_left_alone():
    msg = {"jsonrpc": "2.0", "method": "session/update", "params": {"update": "nope"}}
    assert rewrite_agent_message(msg) is None


def test_unrelated_method_is_left_alone():
    assert rewrite_agent_message({"jsonrpc": "2.0", "id": 1, "result": {}}) is None


# ---------------------------------------------------------------------------
# Proxy: the rewrites in the stream, everything else verbatim
# ---------------------------------------------------------------------------


def _pump(stream, agent_lines):
    client_out = stream()
    proxy = Proxy(
        model="test/model",
        client_in=stream(""),
        client_out=client_out,
        agent_in=stream(),
        agent_out=stream("".join(line + "\n" for line in agent_lines)),
        log=[].append,
    )
    proxy.pump_agent_to_client()
    return client_out.written()


def test_opencode_shell_sequence_reaches_kirocrew_gate_intact(stream):
    """The whole workaround: pending stub dropped, permission params renamed."""
    written = _pump(stream, [json.dumps(_tool_call()), json.dumps(_permission())])

    pending, permission = (json.loads(line) for line in written)
    assert "rawInput" not in pending["params"]["update"]
    assert permission["params"]["toolCall"]["input"] == FULL_PARAMS


def test_frames_without_raw_input_are_relayed_byte_for_byte(stream):
    """The substring gate skips the JSON round-trip, so bytes are preserved."""
    lines = [
        '{"jsonrpc":"2.0","method":"session/update",'
        '"params":{"update":{"sessionUpdate":"agent_message_chunk","text":"hi"}}}',
        '{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":1}}',
    ]
    assert _pump(stream, lines) == lines


def test_malformed_json_is_relayed_not_dropped(stream):
    """Losing a frame would hang an awaited request; let KiroCrew see the junk."""
    line = 'not json at all but mentions "rawInput"'
    assert _pump(stream, [line]) == [line]


def test_non_object_json_is_relayed_not_crashed(stream):
    """A JSON array would AttributeError a dict-only rewrite path."""
    line = '[{"rawInput":{}}]'
    assert _pump(stream, [line]) == [line]
