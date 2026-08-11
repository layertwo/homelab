# kirocrew-opencode

[KiroCrew](https://github.com/kirodotdev/KiroCrew) running against **Ollama Cloud**
instead of a Kiro subscription — with **no patches to KiroCrew**.

## How it works

KiroCrew never talks to an LLM. It spawns an *agent* binary and drives it over
[ACP](https://agentclientprotocol.com) (JSON-RPC 2.0 over newline-delimited
stdio), delegating all model choice to that agent. So supporting Ollama is not a
matter of adding a provider — it's a matter of plugging in an ACP agent that
already speaks Ollama. `opencode` is that agent, and `ollama-cloud` is one of its
built-in providers.

The two don't quite agree on dialect, so this image installs a **translating
proxy** and points `KIROCREW_KIRO_BIN` at it:

```
KiroCrew gateway ──stdio──▶ kirocrew-shim ──stdio──▶ opencode acp ──https──▶ ollama.com
                            (rewrites in flight)
```

The shim stays alive on the pipe rather than `exec`ing, which is the whole trick:
a wrapper that `exec`s vanishes and can only influence argv, while one that stays
sees and can rewrite every message in both directions. That's why no KiroCrew
source patch is needed — and it survives Renovate bumps of KiroCrew, which a
patch would not.

## What gets translated

| Layer | KiroCrew sends | Shim does |
|---|---|---|
| argv | `acp --agent <name>` | strips `--agent` (opencode has no such flag) |
| argv | `--version`, `whoami` probes | answers both; `whoami` must exit 0 or the dashboard reports signed-out and `/api/models` 503s |
| `initialize` | `protocolVersion: "2025-08-22"` | rewrites to integer `1`; standard ACP rejects the string with `-32602` |
| `session/set_mode` | `modeId: <kiro agent>` | answers locally — it's an *awaited* request, so an error would kill the session |
| `session/set_model` | a Kiro canonical model id | substitutes `$OPENCODE_MODEL` |
| `_kiro.dev/*` | proprietary extensions | answers locally so an awaited call can't hang |

## Two behaviours worth knowing

**Permissions are forced on.** `opencode acp` is *unsupervised by default*: it
runs `bash` and file writes while emitting **zero** `session/request_permission`
requests. KiroCrew's governance gate is fed by those requests, so without
`OPENCODE_PERMISSION` the gate is never invoked — not bypassed, never called, and
nothing errors. The shim sets an ask-by-default policy; override
`OPENCODE_PERMISSION` to change it.

**A rejected model is fatal.** With no credential the `ollama-cloud` provider
disappears, `session/set_model` is rejected, and OpenCode then silently answers
the turn from its default free model. The shim kills the agent and exits 1
instead, because a silent downgrade to the wrong model is worse than a crash.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `OPENCODE_MODEL` | `ollama-cloud/gpt-oss:120b` | model substituted into `session/set_model` |
| `OPENCODE_AUTH_CONTENT` | — | **required**; `{"ollama-cloud":{"type":"api","key":"..."}}` |
| `OPENCODE_PERMISSION` | ask for bash/edit/webfetch/task | per-tool `ask`\|`allow`\|`deny` |
| `OPENCODE_BIN` | `opencode` | agent binary to spawn |
| `KIROCREW_KIRO_BIN` | set in the image | must be **absolute** — ACP spawns the agent with `cwd=<session work_dir>` |

`OPENCODE_AUTH_CONTENT` is used rather than mounting an `auth.json`: OpenCode
reads the env var *before* touching the file, and a Secret volume is read-only
while OpenCode's `Auth.set` writes back to `auth.json` (it would `EROFS`).

## Development

```bash
cd containers/kirocrew-opencode
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
pytest                     # 100% coverage required
black src tests && isort src tests && flake8 src tests
```

The suite is pure unit tests — no network, no real agent. `translate.py` holds
the dialect logic as pure functions; `proxy.py` takes its streams by injection so
the pumps can be driven over in-memory buffers. Each test pins one *verified*
incompatibility, so a KiroCrew or OpenCode bump that reintroduces a blocker fails
CI instead of failing quietly in the cluster.

## Verification

Built and run on arm64 (podman) against the real `opencode acp`:

| Check | Result |
|---|---|
| `initialize` with KiroCrew's *unpatched* `"2025-08-22"` string | OK — rewrite works against real opencode |
| `session/new` | OK — real `ses_…` id returned |
| `session/set_mode`, `_kiro.dev/agent_info` | OK — answered locally |
| `session/set_model`, credential present | OK |
| `session/set_model`, **no** credential | `rc=1` + FATAL — fail-fast fires as designed |
| `/api/health` | `200 {"ok":true,"app":"kirocrew","version":"0.2.0"}` |
| entrypoint sandbox probe | `unshare` works → seeded `agent.sandbox=auto` |
| `--version` / `whoami` probes as uid 1000 | both exit 0 |

Two caveats on that table. The credential used was a **dummy** — it proves the
`ollama-cloud` provider *registers*, not that inference authenticates. And
`/api/models` returns **403** (dashboard auth), not 503, so it says nothing about
agent readiness; `/api/health` is unauthenticated, which is why the probes use it.

`systemd-run` is absent from the base image, so KiroCrew logs a SECURITY warning
that per-subprocess cgroup v2 `pids.max`/`memory.max` are unenforced. The pod's
memory limit is the real ceiling on a runaway tool call.

## Deployment

The k3s manifests land separately, in `clusters/home/apps/cloud/kirocrew/`. Notes
for whoever wires them up:

- **Single instance, always.** ACP is stdio between the gateway and a process it
  spawns, so `strategy: Recreate` is load-bearing; never scale past 1.
- **Not read-only rootfs.** The gateway writes config and state under
  `/home/kirocrew` and agent tools write into session work dirs. Capabilities are
  dropped and privilege escalation disabled instead.
- **First-run sandbox decision sticks.** The upstream entrypoint probes for a
  sandbox backend and seeds `sandbox_allow_unsandboxed_exec` only when
  `config.json` is absent. Because the PVC persists `/home/kirocrew`, that
  decision is made once; the file is operator-owned afterwards.

Fuller background and the ACP spike log live in
`docs/superpowers/specs/2026-08-10-kirocrew-ollama-design.md` (also added
separately); this README is self-contained without it.
