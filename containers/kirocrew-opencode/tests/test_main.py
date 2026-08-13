import json
import subprocess

import pytest

from kirocrew_shim import main as main_module
from kirocrew_shim.main import main
from kirocrew_shim.proxy import ModelRejected


class FakePopen:
    """Stands in for `opencode acp`, recording how it was invoked."""

    instances = []

    def __init__(self, argv, **kwargs):
        self.argv = argv
        self.kwargs = kwargs
        self.stdin = object()
        self.stdout = object()
        self.killed = False
        self.wait_code = 0
        FakePopen.instances.append(self)

    def kill(self):
        self.killed = True

    def wait(self):
        return self.wait_code


@pytest.fixture
def fake_popen(monkeypatch):
    FakePopen.instances = []
    monkeypatch.setattr(main_module.subprocess, "Popen", FakePopen)
    return FakePopen


@pytest.fixture
def fake_proxy(monkeypatch):
    """Replace Proxy.run so main() can be tested without real streams."""
    calls = {}

    def install(behaviour):
        def run(self):
            calls["model"] = self.model
            behaviour()

        monkeypatch.setattr(main_module.Proxy, "run", run)
        return calls

    return install


def test_version_probe_short_circuits_before_spawning(monkeypatch, capsys, fake_popen):
    monkeypatch.setattr("sys.argv", ["kirocrew-shim", "--version"])
    assert main() == 0
    assert "kirocrew-shim" in capsys.readouterr().out
    assert fake_popen.instances == []


def test_unknown_probe_exits_zero_silently(monkeypatch, capsys, fake_popen):
    monkeypatch.setattr("sys.argv", ["kirocrew-shim", "mystery"])
    assert main() == 0
    assert capsys.readouterr().out == ""
    assert fake_popen.instances == []


@pytest.fixture
def fake_run(monkeypatch):
    """Replace subprocess.run so the `opencode models` spawn is a stand-in."""
    calls = []

    def install(behaviour):
        def run(argv, **kwargs):
            calls.append(argv)
            return behaviour(argv, **kwargs)

        monkeypatch.setattr(main_module.subprocess, "run", run)
        return calls

    return install


def test_list_models_probe_queries_opencode_for_the_configured_provider(
    monkeypatch, capsys, fake_popen, fake_run
):
    monkeypatch.setenv("OPENCODE_MODEL", "ollama-cloud/qwen3-coder:480b")
    monkeypatch.setattr(
        "sys.argv",
        ["kirocrew-shim", "chat", "--list-models", "--format", "json", "--no-interactive"],
    )
    calls = fake_run(
        lambda argv, **kwargs: subprocess.CompletedProcess(
            argv, 0, stdout="ollama-cloud/gpt-oss:120b\nollama-cloud/qwen3-coder:480b\n"
        )
    )

    assert main() == 0

    assert calls == [["opencode", "models", "ollama-cloud"]]
    payload = json.loads(capsys.readouterr().out)
    assert payload["models"] == [
        {"model_name": "ollama-cloud/gpt-oss:120b"},
        {"model_name": "ollama-cloud/qwen3-coder:480b"},
    ]
    assert fake_popen.instances == []


def test_list_models_probe_falls_back_when_opencode_spawn_fails(
    monkeypatch, capsys, fake_popen, fake_run
):
    # A hung/errored `opencode models` must degrade to the one model we know
    # is configured, not resurface as api_models' empty-output 503.
    monkeypatch.setenv("OPENCODE_MODEL", "ollama-cloud/gpt-oss:120b")
    monkeypatch.setattr(
        "sys.argv",
        ["kirocrew-shim", "chat", "--list-models", "--format", "json", "--no-interactive"],
    )

    def timeout(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, 8)

    fake_run(timeout)

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload == {"models": [{"model_name": "ollama-cloud/gpt-oss:120b"}]}
    assert fake_popen.instances == []


def test_acp_spawns_opencode_with_stripped_args(monkeypatch, fake_popen, fake_proxy):
    monkeypatch.setattr("sys.argv", ["kirocrew-shim", "acp", "--agent", "kirocrew"])
    fake_proxy(lambda: None)

    assert main() == 0

    child = fake_popen.instances[0]
    assert child.argv == ["opencode", "acp"]
    # Line buffering matters: ACP is newline-delimited, so a block-buffered
    # pipe would stall the handshake.
    assert child.kwargs["bufsize"] == 1
    assert child.kwargs["text"] is True
    assert "OPENCODE_PERMISSION" in child.kwargs["env"]


def test_model_override_is_passed_to_the_proxy(monkeypatch, fake_popen, fake_proxy):
    monkeypatch.setenv("OPENCODE_MODEL", "ollama-cloud/qwen3-coder:480b")
    monkeypatch.setattr("sys.argv", ["kirocrew-shim", "acp"])
    calls = fake_proxy(lambda: None)

    main()
    assert calls["model"] == "ollama-cloud/qwen3-coder:480b"


def test_child_exit_code_is_propagated(monkeypatch, fake_popen, fake_proxy):
    monkeypatch.setattr("sys.argv", ["kirocrew-shim", "acp"])
    fake_proxy(lambda: None)

    def spawn(argv, **kwargs):
        child = FakePopen(argv, **kwargs)
        child.wait_code = 3
        return child

    monkeypatch.setattr(main_module.subprocess, "Popen", spawn)
    assert main() == 3


def test_model_rejection_kills_the_agent_and_exits_one(monkeypatch, fake_popen, fake_proxy):
    monkeypatch.setattr("sys.argv", ["kirocrew-shim", "acp"])

    def reject():
        raise ModelRejected("ollama-cloud/gpt-oss:120b")

    fake_proxy(reject)

    assert main() == 1
    assert fake_popen.instances[0].killed is True
