# Tunnels

Self-hosted, ngrok-style HTTP tunnels using the [tunnels CLI and broker](https://github.com/layertwo/tunnels)
and [frp](https://github.com/fatedier/frp). Publish a local web app at
`https://<handle>[-<name>].w.tunnels.layertwo.dev` and sign in with Pocket ID to open it.

**Phase 1 is owner-only.** Being in `tunnels-viewers` lets you authenticate at the browser gate;
it does not grant access to another person's tunnel. Sharing is a later phase.

## Set up a creator

1. Add their Pocket ID account to `tunnels-creators` (the group's **Name**, not its Friendly name).
2. Their username, lowercased, must be 2–20 ASCII letters/digits. Handles are assigned at first login
   and remain tied to the account's subject ID. Keep self-service username changes disabled in
   Pocket ID: otherwise someone could rename themselves to an unclaimed handle before its owner logs in.
3. Download the appropriate archive and `checksums.txt` from
   [Releases](https://github.com/layertwo/tunnels/releases/tag/v0.1.0), verify it, and put `tunnel`
   (`tunnel.exe` on Windows) on `PATH`.

For example, on an Apple Silicon Mac:

```sh
gh attestation verify tunnel_0.1.0_darwin_arm64.tar.gz --repo layertwo/tunnels
grep ' tunnel_0.1.0_darwin_arm64.tar.gz$' checksums.txt | shasum -a 256 -c -
tar -xzf tunnel_0.1.0_darwin_arm64.tar.gz
```

Phase 0 machine-client configs are no longer supported by this deployment. Use the CLI's user
login instead; server-side machine-client mappings are a later feature.

## Run a tunnel

```sh
tunnel version
tunnel login                 # approve the displayed URL/code in Pocket ID
tunnel up 3000               # https://<handle>.w.tunnels.layertwo.dev
tunnel up 3000 --name blog   # https://<handle>-blog.w.tunnels.layertwo.dev
tunnel logout                # delete this computer's stored login
```

`tunnel up` forwards to `http://127.0.0.1:<port>` and runs until stopped. The CLI verifies the
server certificate using its embedded CA bundle, refreshes tokens every 30 minutes, and reconnects
after a connection drops. It prints a refusal reason if its first login or proxy registration fails.

- A tunnel name is 1–42 lowercase ASCII letters/digits/inner hyphens; `default` is reserved.
- The configured cap is five active tunnels per creator and 10MB/s per tunnel, enforced by frps.
  The count cap is soft during simultaneous registrations because the dashboard can lag.
- Login files live in `tunnels/` under the OS config directory, or `$TUNNELS_CONFIG_DIR`, with
  mode 0600. On macOS this is `~/Library/Application Support/tunnels`; on Linux normally
  `~/.config/tunnels`; on Windows `%AppData%\tunnels`.

Open the printed URL in your browser and sign in as the same Pocket ID account. Another user
gets an empty 403, even if they are also a creator. Unknown owners and denied access look the same.

## How it works

| Piece | Path |
|---|---|
| Control | CLI → Cloudflare/external Traefik → frps:7000 at `/~!frp`; native frp over WSS |
| API/discovery | External Traefik → broker:8080 for `/api/me`, `/.well-known/tunnels.json`, `/healthz` |
| Visitors | External Traefik strips supplied identity → Pocket ID gate → broker `/authz` → strips internal identity → rate/in-flight limits → frps:8080 |
| Ownership | Broker verifies creator tokens, resolves Pocket ID userinfo, and binds names to the stored handle |
| State | `cnpg-tunnels`, one PostgreSQL instance; the broker migrates the schema at startup |
| Internal frps API | Broker alone reaches authenticated dashboard frps:7500; frps reaches the broker plugin |

The wildcard sites DNS is unproxied and uses the existing `tunnels-sites-tls` certificate.
The apex remains Cloudflare-proxied. Public routing excludes `/authz`, `/plugin/`, and the dashboard.

A tunneled app receives its site `Host`, `X-Forwarded-For`, `X-Forwarded-Proto: https`, and
`X-Tunnel-User` (the authorized visitor's username). Internal `X-Tunnels-*` headers and the gate's
cookies are removed; the app's own cookies and WebSockets still work. The browser gate currently
owns `/oidc/callback` and paths starting with `/logout` on each site.

## Operations

Manifests: `clusters/home/apps/network/tunnels/`. The broker/frps images are the signed `v0.1.0`
release pinned by digest. They run non-root with read-only filesystems and no Kubernetes API token.
NetworkPolicies isolate public ingress, the plugin, dashboard, and database. CNPG instance management
is permitted from the operator in namespace `default`; database egress is left open for bootstrap
and Kubernetes API access.

The public device-flow client is `tunnels-cli`, ID `dbf1099c-ebad-4c97-b1da-137372140feb`, with
user-delegated access to the Tunnels API resource `https://tunnels.layertwo.dev`. It has no client
secret. Its device flow, signed token audience, userinfo and refresh were verified against Pocket ID.
The browser gate keeps its separate confidential client `tunnels-gate` and encrypted credentials.

Plugin/dashboard credentials are SOPS-encrypted in `broker/secrets-broker.sops.yml` and
`frps/secrets-frps.sops.yml`. Rotate them together. frps includes the plugin URL in errors if the
broker is unreachable; treat those logs as secret-bearing. Database credentials come from
CNPG's generated `cnpg-tunnels-app` Secret (`uri`).

`/healthz` means the broker HTTP server is running; it is not a database or Pocket ID readiness
check. Database failure makes authorization return 503 and prevents new creator logins/registrations.

### Validate before merging

With `kubectl`, Helm and PyYAML available:

```sh
helm repo add bjw-s https://bjw-s-labs.github.io/helm-charts
helm repo update bjw-s
python3 scripts/check-tunnels.py
# With the production age key available, also validate matching private credentials and frps TOML:
python3 scripts/check-tunnels.py --decrypt
```

The check renders app-template 5.2.1 and verifies service/credential wiring, workload hardening,
NetworkPolicy allow/deny cases, private endpoint exclusion, and the site authorization chain.
Review the draft PR's `flux-diff` output as well. Rendering does not prove cluster reconciliation.

### Acceptance after deployment

Verify broker/frps HelmReleases and CNPG readiness, then test the released CLI against a disposable
local HTTP server. Check owner access, cross-user denial, forged identity/forwarded-host denial,
stolen-name rejection, HTTP/WebSocket traffic and the app's received headers. Confirm dependency
failure cannot allow access and that private routes remain unavailable publicly.

### Revocation

Creator access tokens last one hour with the current Pocket ID defaults. Removing a creator from
the group prevents further authorized refreshes; an existing token can remain usable until expiry,
with a 90-second heartbeat timeout backstop. Instant removal is a later feature.

`tunnel logout` only removes local files. Pocket ID advertises no token-revocation endpoint;
a copied refresh token must be dealt with in Pocket ID. Stop running tunnels explicitly when logging
out. Visitors removed from gate groups lose access when the gate refreshes/rechecks their session.

## Troubleshooting

| Symptom | Check |
|---|---|
| Cannot reach discovery or `/api/me` | Broker readiness, apex route, NetworkPolicy, Flux reconciliation |
| `invalid_target` during login | CLI client has user-delegated access to the Tunnels API resource |
| Login refuses creator access | Account belongs to `tunnels-creators`; compare the group's Name exactly |
| Username cannot form a handle | Use 2–20 ASCII letters/digits; reserved handles are refused |
| Certificate verification fails | Correct hostname, Traefik certificate and trust chain; do not disable verification |
| Owner receives 403 | Browser and CLI use the same Pocket ID subject; verify gate identity and middleware order |
| Another creator/viewer receives 403 | Expected: Phase 1 has no sharing |
| Visitors receive 503 | Broker cannot look up ownership in PostgreSQL |
| A new tunnel is refused while broker is running | Check database, Pocket ID and private dashboard connectivity |
| Limit reached after a disconnect | A dropped client can remain counted until frps's 90-second heartbeat timeout |
| A script receives 401 instead of a browser redirect | The gate redirects HTML requests; non-browser API access to sites is not implemented |

See the [deployment plan](plans/2026-10-10-tunnels-phase1-deployment-plan.md) and the
[current application design](https://github.com/layertwo/tunnels/blob/mainline/docs/design.md).
