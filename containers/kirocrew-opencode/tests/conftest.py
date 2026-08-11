import io

import pytest


@pytest.fixture
def model() -> str:
    return "ollama-cloud/gpt-oss:120b"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Keep a developer's real OpenCode config out of the tests."""
    for key in ("OPENCODE_MODEL", "OPENCODE_BIN", "OPENCODE_PERMISSION"):
        monkeypatch.delenv(key, raising=False)


class Stream(io.StringIO):
    """A StringIO that records flushes and survives close() for assertions."""

    def __init__(self, initial: str = ""):
        super().__init__(initial)
        self.closed_count = 0

    def close(self) -> None:  # keep the buffer readable after the pump closes it
        self.closed_count += 1

    def written(self) -> list:
        return [line for line in self.getvalue().splitlines() if line]


@pytest.fixture
def stream():
    return Stream
