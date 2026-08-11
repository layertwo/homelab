import json
import os
from functools import cached_property

# OpenCode's ACP mode runs bash/edit UNSUPERVISED by default -- verified against
# opencode 1.18.16: a `uname -a` and a file write both executed while emitting
# ZERO session/request_permission requests. KiroCrew's governance gate is *fed
# by* those requests, so without this it is never invoked -- not bypassed,
# never called, and nothing errors. Force ask-by-default.
DEFAULT_PERMISSION = {
    "bash": "ask",
    "edit": "ask",
    "webfetch": "ask",
    "task": "ask",
    "external_directory": "ask",
}

DEFAULT_MODEL = "ollama-cloud/gpt-oss:120b"


class Settings:

    @cached_property
    def model(self) -> str:
        return os.environ.get("OPENCODE_MODEL", DEFAULT_MODEL)

    @cached_property
    def opencode_bin(self) -> str:
        return os.environ.get("OPENCODE_BIN", "opencode")

    @cached_property
    def child_env(self) -> dict:
        """Environment for the spawned agent, with permissions forced on."""
        env = dict(os.environ)
        env.setdefault("OPENCODE_PERMISSION", json.dumps(DEFAULT_PERMISSION))
        return env
