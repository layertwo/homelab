"""Pure translation between KiroCrew's ACP dialect and standard ACP.

No I/O happens here: every function takes decoded values and returns decoded
values, so the whole dialect gap is unit-testable without spawning an agent.

The four verified incompatibilities, all absorbed here rather than by patching
KiroCrew (see docs/superpowers/specs/2026-08-10-kirocrew-ollama-design.md):

  argv               `--version` / `whoami` probes; the unsupported `--agent`
  initialize         protocolVersion string -> int
  session/set_mode   answered locally (OpenCode has no kiro modes)
  session/set_model  Kiro model id -> the configured OpenCode model
  _kiro.dev/*        answered locally so an awaited call cannot hang
"""

import json
from typing import Any, NamedTuple, Optional

VERSION = "0.1.0"

# Standard ACP requires an INTEGER protocolVersion; KiroCrew sends the
# Kiro-proprietary string "2025-08-22" (src/kiro_crew/acp/client.py:135), which
# standard agents reject with -32602 "expected number, received string".
ACP_PROTOCOL_VERSION = 1

# kiro_prerequisite.py gates `ready` on `whoami` exiting 0; if it fails the
# dashboard reports signed-out and /api/models returns 503.
WHOAMI_OUTPUT = "Authenticated with API key"

FORWARD = "forward"  # pass the (possibly rewritten) message on to the agent
REPLY = "reply"  # answer locally; never reaches the agent
DROP = "drop"  # swallow entirely


class ArgvPlan(NamedTuple):
    """What to do with the argv KiroCrew invoked us with.

    An `exit_code` of None means "proceed to proxying"; anything else means
    print `message` (when non-empty) and exit with that code.
    """

    exit_code: Optional[int] = None
    message: str = ""
    agent_args: tuple = ()


class Decision(NamedTuple):
    """How to handle one client->agent message.

    `watch_model_id` carries the request id of a session/set_model call so the
    caller can detect a rejection; see Proxy for why that matters.
    """

    action: str
    payload: Optional[dict] = None
    watch_model_id: Any = None


def plan_argv(argv) -> ArgvPlan:
    """Decide what KiroCrew's invocation means.

    KiroCrew spawns `[bin, "acp", "--agent", <name>]` (client.py:2339), but
    `opencode acp` accepts no `--agent` flag, so it is stripped.
    """
    head = argv[:1]

    if head == ["--version"]:
        return ArgvPlan(exit_code=0, message=f"kirocrew-shim {VERSION}")
    if head == ["whoami"]:
        return ArgvPlan(exit_code=0, message=WHOAMI_OUTPUT)
    if head != ["acp"]:
        # Tolerate probes we don't model: exiting 0 silently is friendlier than
        # failing a prerequisite check over an unknown subcommand.
        return ArgvPlan(exit_code=0)

    return ArgvPlan(agent_args=tuple(_strip_agent_flag(argv[1:])))


def _strip_agent_flag(args):
    """Drop `--agent <name>` pairs; opencode acp has no such flag."""
    kept, i = [], 0
    while i < len(args):
        if args[i] == "--agent":
            i += 2  # also skips its value; a trailing --agent just ends the loop
            continue
        kept.append(args[i])
        i += 1
    return kept


def _ok(request_id) -> Decision:
    """Answer a request locally with an empty result, or drop a notification."""
    if request_id is None:
        return Decision(DROP)
    return Decision(REPLY, {"jsonrpc": "2.0", "id": request_id, "result": {}})


def translate_client_message(msg: dict, model: str) -> Decision:
    """Map one KiroCrew->agent message into an action for the caller."""
    method = msg.get("method")
    params = msg.get("params") or {}
    request_id = msg.get("id")

    if method == "initialize":
        params["protocolVersion"] = ACP_PROTOCOL_VERSION
        return Decision(FORWARD, {**msg, "params": params})

    # KiroCrew's modeId is a kiro agent name, meaningless to OpenCode (which
    # picks its agent from config) and sent via an AWAITED request, so an error
    # propagates and kills the session. Answering locally also means no
    # OpenCode `agent` config entry is needed.
    if method == "session/set_mode":
        return _ok(request_id)

    # Kiro's canonical model ids don't exist in OpenCode. Proven to be a real
    # substitution rather than a no-op by negative control: a bogus id yields
    # -32602 "model not found: ollama-cloud/does-not-exist", naming a string
    # KiroCrew never sent.
    if method == "session/set_model":
        params["modelId"] = model
        return Decision(FORWARD, {**msg, "params": params}, watch_model_id=request_id)

    # Proprietary Kiro extensions: answer locally rather than let an awaited
    # call hang on an agent that has never heard of them.
    if method and method.startswith("_kiro.dev/"):
        return _ok(request_id)

    return Decision(FORWARD, msg)


def rejected_request_id(line: str):
    """Return the request id if *line* is a JSON-RPC error response, else None.

    The substring check short-circuits the JSON parse: a single turn streams
    many chunk notifications, and none of them need decoding.
    """
    if '"error"' not in line:
        return None
    try:
        msg = json.loads(line)
    except json.JSONDecodeError:
        return None
    if isinstance(msg, dict) and "error" in msg:
        return msg.get("id")
    return None
