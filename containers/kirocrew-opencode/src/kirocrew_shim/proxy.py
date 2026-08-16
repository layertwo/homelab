"""The stdio plumbing: two pump threads moving ndjson between client and agent.

Why a proxy and not a wrapper: a wrapper that `exec`s vanishes from the pipe and
can only influence argv. One that stays alive owns both directions of the stream
and can rewrite every message -- which is what makes zero KiroCrew patches
possible. `exec` vs. proxy is the whole distinction.
"""

import json
import threading

from kirocrew_shim.translate import (
    DROP,
    REPLY,
    rejected_request_id,
    rewrite_agent_message,
    translate_client_message,
)

MODEL_REJECTED_MESSAGE = (
    "kirocrew-shim: FATAL: agent rejected model {model!r}. Refusing to continue -- "
    "OpenCode would silently serve this turn from its default model. "
    "Check OPENCODE_AUTH_CONTENT / auth.json."
)


def _rewritten(line: str) -> str:
    """Apply the agent->client rewrites, or return *line* untouched.

    Anything that is not a JSON object is relayed as-is: a malformed frame is
    the agent's bug, and forwarding it lets KiroCrew report the real error
    instead of the session silently losing a message.
    """
    try:
        msg = json.loads(line)
    except json.JSONDecodeError:
        return line
    if not isinstance(msg, dict):
        return line
    rewritten = rewrite_agent_message(msg)
    return line if rewritten is None else json.dumps(rewritten)


class ModelRejected(Exception):
    """The agent refused the model we substituted.

    Verified failure mode: with no credential the ollama-cloud provider vanishes,
    session/set_model returns -32602 "model not found", and OpenCode then
    silently answers the turn from its default free model (opencode/big-pickle --
    88 input tokens vs. 6,226 for the real model). A silent downgrade to the
    wrong model is worse than a crash, so fail loudly instead.
    """

    def __init__(self, model: str):
        self.model = model
        super().__init__(MODEL_REJECTED_MESSAGE.format(model=model))


class Proxy:
    """Pumps messages between KiroCrew (client) and the agent.

    Streams are injected rather than reached for globally so the pumps can be
    driven over in-memory buffers in tests.
    """

    def __init__(self, model, client_in, client_out, agent_in, agent_out, log):
        self.model = model
        self.client_in = client_in
        self.client_out = client_out
        self.agent_in = agent_in
        self.agent_out = agent_out
        self.log = log
        # Both pumps write to client_out (local replies from one, agent traffic
        # from the other), so serialize to avoid interleaved half-lines.
        self._out_lock = threading.Lock()
        self._pending_model = {}

    def _write(self, stream, obj) -> None:
        stream.write(json.dumps(obj) + "\n")
        stream.flush()

    def _to_client(self, obj) -> None:
        with self._out_lock:
            self._write(self.client_out, obj)

    def pump_client_to_agent(self) -> None:
        for line in self.client_in:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                # A malformed line is the client's bug; dropping it keeps the
                # session alive rather than tearing down the proxy.
                continue

            decision = translate_client_message(msg, self.model)
            if decision.action == REPLY:
                self._to_client(decision.payload)
                continue
            if decision.action == DROP:
                continue

            if decision.watch_model_id is not None:
                # The id actually forwarded, not self.model: translate_client_message
                # now passes the client's pick through, so a rejection must name
                # what was really requested, not the (mere fallback) default.
                self._pending_model[decision.watch_model_id] = decision.payload["params"]["modelId"]
            self._write(self.agent_in, decision.payload)

        self._close_agent_stdin()

    def _close_agent_stdin(self) -> None:
        try:
            self.agent_in.close()
        except Exception:  # pragma: no cover - stream already torn down
            pass

    def pump_agent_to_client(self) -> None:
        """Forward agent output, raising ModelRejected on a set_model error.

        Frames carrying tool params are rewritten on the way past so KiroCrew's
        deny-by-default shell gate can see the command (see translate's module
        docstring); everything else is relayed byte-for-byte.
        """
        for line in self.agent_out:
            line = line.rstrip("\n")
            if not line.strip():
                continue

            # Substring gate before the JSON parse: only rawInput-bearing frames
            # are ever rewritten, and a single turn streams thousands of chunk
            # notifications that would otherwise be decoded for nothing.
            if '"rawInput"' in line:
                line = _rewritten(line)

            if self._pending_model:
                request_id = rejected_request_id(line)
                # `is not None` matters: a JSON-RPC id may legitimately be 0.
                if request_id is not None and request_id in self._pending_model:
                    # Log the exception's own message so the two can never drift.
                    rejected = ModelRejected(self._pending_model.pop(request_id))
                    self.log(str(rejected))
                    raise rejected

            with self._out_lock:
                self.client_out.write(line + "\n")
                self.client_out.flush()

    def run(self) -> None:
        """Pump both directions, returning when the agent's output ends.

        The client pump is a daemon thread: KiroCrew holds our stdin open for the
        gateway's lifetime, so a join would block forever after the agent exits.
        """
        thread = threading.Thread(target=self.pump_client_to_agent, daemon=True)
        thread.start()
        self.pump_agent_to_client()
