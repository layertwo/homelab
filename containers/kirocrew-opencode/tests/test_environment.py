import json

from kirocrew_shim.environment import DEFAULT_MODEL, DEFAULT_PERMISSION, Settings


def test_model_defaults_to_ollama_cloud():
    assert Settings().model == DEFAULT_MODEL


def test_model_is_overridable(monkeypatch):
    monkeypatch.setenv("OPENCODE_MODEL", "ollama-cloud/qwen3-coder:480b")
    assert Settings().model == "ollama-cloud/qwen3-coder:480b"


def test_opencode_bin_defaults_to_path_lookup():
    assert Settings().opencode_bin == "opencode"


def test_opencode_bin_is_overridable(monkeypatch):
    monkeypatch.setenv("OPENCODE_BIN", "/opt/opencode/bin/opencode")
    assert Settings().opencode_bin == "/opt/opencode/bin/opencode"


def test_child_env_forces_permissions_on():
    # Without this the agent runs bash and file writes with ZERO
    # session/request_permission requests, so KiroCrew's governance gate is
    # never invoked -- silently, since nothing errors.
    permission = json.loads(Settings().child_env["OPENCODE_PERMISSION"])
    assert permission == DEFAULT_PERMISSION
    assert permission["bash"] == "ask"
    assert permission["edit"] == "ask"


def test_child_env_respects_an_operator_override(monkeypatch):
    monkeypatch.setenv("OPENCODE_PERMISSION", '{"bash":"deny"}')
    assert Settings().child_env["OPENCODE_PERMISSION"] == '{"bash":"deny"}'


def test_child_env_inherits_the_credential(monkeypatch):
    # The gateway entrypoint scrubs channel tokens from the environ, but its
    # CRED_KEYS allowlist covers channel tokens only, so this passes through.
    monkeypatch.setenv("OPENCODE_AUTH_CONTENT", '{"ollama-cloud":{"type":"api","key":"k"}}')
    assert "OPENCODE_AUTH_CONTENT" in Settings().child_env
