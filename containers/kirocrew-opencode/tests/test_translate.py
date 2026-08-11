"""Each test here pins one verified incompatibility from the 2026-08-10 spike.

If a KiroCrew or OpenCode bump reintroduces a blocker, these fail in CI rather
than failing silently in the cluster.
"""

import pytest

from kirocrew_shim.translate import (
    ACP_PROTOCOL_VERSION,
    DROP,
    FORWARD,
    REPLY,
    VERSION,
    WHOAMI_OUTPUT,
    plan_argv,
    rejected_request_id,
    translate_client_message,
)


def test_version_probe_exits_zero():
    plan = plan_argv(["--version"])
    assert plan.exit_code == 0
    assert VERSION in plan.message


def test_whoami_probe_reports_authenticated():
    # kiro_prerequisite gates `ready` on this exiting 0; a failure makes the
    # dashboard report signed-out and /api/models return 503.
    plan = plan_argv(["whoami"])
    assert plan.exit_code == 0
    assert plan.message == WHOAMI_OUTPUT


def test_unknown_subcommand_exits_zero_without_output():
    plan = plan_argv(["some-future-probe"])
    assert plan.exit_code == 0
    assert plan.message == ""


def test_no_args_is_not_treated_as_acp():
    assert plan_argv([]).exit_code == 0


def test_acp_proceeds_to_proxying():
    plan = plan_argv(["acp"])
    assert plan.exit_code is None
    assert plan.agent_args == ()


def test_agent_flag_and_its_value_are_stripped():
    # KiroCrew spawns [bin, "acp", "--agent", <name>] (client.py:2339) but
    # `opencode acp` accepts no --agent flag.
    plan = plan_argv(["acp", "--agent", "kirocrew"])
    assert plan.agent_args == ()


def test_other_flags_survive_stripping():
    plan = plan_argv(["acp", "--agent", "kirocrew", "--verbose", "--port", "1234"])
    assert plan.agent_args == ("--verbose", "--port", "1234")


def test_trailing_agent_flag_without_value_does_not_hang():
    assert plan_argv(["acp", "--agent"]).agent_args == ()


def test_initialize_protocol_version_string_becomes_int(model):
    # KiroCrew sends PROTOCOL_VERSION = "2025-08-22" (client.py:135); standard
    # ACP requires an integer and rejects the string with -32602.
    msg = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2025-08-22"},
    }
    decision = translate_client_message(msg, model)
    assert decision.action == FORWARD
    assert decision.payload["params"]["protocolVersion"] == ACP_PROTOCOL_VERSION
    assert isinstance(decision.payload["params"]["protocolVersion"], int)


def test_initialize_preserves_other_params(model):
    msg = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2025-08-22", "clientCapabilities": {"fs": {}}},
    }
    decision = translate_client_message(msg, model)
    assert decision.payload["params"]["clientCapabilities"] == {"fs": {}}


def test_initialize_without_params_still_sets_version(model):
    decision = translate_client_message({"id": 1, "method": "initialize"}, model)
    assert decision.payload["params"]["protocolVersion"] == ACP_PROTOCOL_VERSION


def test_set_mode_is_answered_locally(model):
    # Sent via an AWAITED request, so letting the agent error out kills the
    # session; answering locally also avoids needing an OpenCode agent config.
    msg = {
        "jsonrpc": "2.0",
        "id": 7,
        "method": "session/set_mode",
        "params": {"modeId": "kirocrew"},
    }
    decision = translate_client_message(msg, model)
    assert decision.action == REPLY
    assert decision.payload == {"jsonrpc": "2.0", "id": 7, "result": {}}


def test_set_mode_notification_is_dropped(model):
    decision = translate_client_message({"method": "session/set_mode"}, model)
    assert decision.action == DROP
    assert decision.payload is None


def test_set_model_id_is_substituted(model):
    msg = {
        "jsonrpc": "2.0",
        "id": 9,
        "method": "session/set_model",
        "params": {"sessionId": "s1", "modelId": "some-kiro-canonical-id"},
    }
    decision = translate_client_message(msg, model)
    assert decision.action == FORWARD
    assert decision.payload["params"]["modelId"] == model
    assert decision.payload["params"]["sessionId"] == "s1"


def test_set_model_is_watched_for_rejection(model):
    msg = {"jsonrpc": "2.0", "id": 9, "method": "session/set_model", "params": {}}
    assert translate_client_message(msg, model).watch_model_id == 9


def test_kiro_extension_request_is_answered_locally(model):
    # Answer locally rather than let an awaited call hang on an agent that has
    # never heard of the method.
    msg = {"jsonrpc": "2.0", "id": 11, "method": "_kiro.dev/some_extension"}
    decision = translate_client_message(msg, model)
    assert decision.action == REPLY
    assert decision.payload["id"] == 11


def test_kiro_extension_notification_is_dropped(model):
    decision = translate_client_message({"method": "_kiro.dev/telemetry"}, model)
    assert decision.action == DROP


@pytest.mark.parametrize(
    "method",
    ["session/new", "session/prompt", "session/cancel", "authenticate"],
)
def test_unrelated_methods_pass_through_untouched(method, model):
    msg = {"jsonrpc": "2.0", "id": 3, "method": method, "params": {"a": 1}}
    decision = translate_client_message(msg, model)
    assert decision.action == FORWARD
    assert decision.payload == msg


def test_response_without_method_passes_through(model):
    # KiroCrew's replies to agent-initiated requests (e.g. permission outcomes)
    # carry no method and must not be mistaken for a translatable call.
    msg = {"jsonrpc": "2.0", "id": 4, "result": {"outcome": {"outcome": "selected"}}}
    decision = translate_client_message(msg, model)
    assert decision.action == FORWARD
    assert decision.payload == msg


def test_error_response_id_is_detected():
    line = '{"jsonrpc":"2.0","id":9,"error":{"code":-32602,"message":"model not found"}}'
    assert rejected_request_id(line) == 9


def test_zero_is_a_valid_error_id():
    # Guards the `is not None` check in the proxy: a falsy-but-real id.
    assert rejected_request_id('{"id":0,"error":{"code":-1,"message":"x"}}') == 0


def test_success_response_is_not_an_error():
    assert rejected_request_id('{"jsonrpc":"2.0","id":9,"result":{}}') is None


def test_notification_mentioning_error_text_is_not_an_error():
    # The word "error" inside content must not trip the cheap substring check
    # into reporting a rejection.
    line = '{"method":"session/update","params":{"text":"the \\"error\\" was fixed"}}'
    assert rejected_request_id(line) is None


def test_malformed_json_is_not_an_error_id():
    assert rejected_request_id('{"error": truncated...') is None


def test_non_object_json_is_not_an_error_id():
    assert rejected_request_id('["error"]') is None
