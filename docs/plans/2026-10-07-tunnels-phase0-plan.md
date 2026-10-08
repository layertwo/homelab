# Tunnels Phase 0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put stock-only tunnels on the cluster: frps, the existing Traefik OIDC plugin as a login gate, and the wildcard DNS and certificate. A person with a Pocket ID machine client can then publish an HTTP service at `<handle>.w.tunnels.layertwo.dev` behind a Pocket ID login, and the cluster-side unknowns are settled before any Go is written.

**Architecture:** frps (official image, no plugin) takes wss control connections on `tunnels.layertwo.dev/~!frp` through the external Traefik and serves site traffic on 8080. Sites sit behind the `traefik-oidc-auth` middleware, which admits the groups `tunnel-viewers` and `tunnel-creators`. Creators authenticate to frps with Pocket ID machine clients (client credentials), so names are trust-based in this phase.

**Tech Stack:** Flux CD, bjw-s `app-template` 5.2.1, SOPS/age, Traefik (external) with traefik-oidc-auth, cert-manager, external-dns, Pocket ID v2.18.0, frp v0.71.0.

**Spec:** `docs/plans/2026-10-07-tunnels-design.md` (Phasing, Verification, Networking and TLS, frps). Read it first; every value below is justified there.

**Scope:** This is plan 1 of 4. Plans 2-4 cover the Go repo and are written after Task 4 records its results, because those results can change them: plan 2 = broker hooks, `/authz`, CLI `login`/`up`, releases (design phase 1); plan 3 = sharing (phase 2); plan 4 = hardening, machine-client mapping, `tunnels-frps` distroless image (phase 3).

## Global Constraints

- Namespace `tunnels`; manifests under `clusters/home/apps/network/tunnels/`. No change to existing Traefik, Pocket ID or any other namespace.
- Hosts: service `tunnels.layertwo.dev` (proxied); sites `<handle>[-<name>].w.tunnels.layertwo.dev` (DNS-only wildcard `*.w.tunnels.layertwo.dev`).
- frps image `ghcr.io/fatedier/frps:v0.71.0@sha256:cd8b947ba61678b200baa4f71ccc33f3c52e4e2cc0059700ba3b8354e36af7c3`; frpc image `ghcr.io/fatedier/frpc:v0.71.0@sha256:99ece6a2b62cfc68731e0df289af804ff1c699911cfc47871856434f1d6d53ee`. Images come from ghcr.io, not Docker Hub (upstream pushes identical digests to both).
- Chart `app-template` `5.2.1` from HelmRepository `bjw-s` in `flux-system`, as every other release here.
- frps: `bindPort = 7000`, `vhostHTTPPort = 8080`, `subDomainHost = "w.tunnels.layertwo.dev"`, `auth.method = "oidc"`, `auth.oidc.issuer = "https://idp.layertwo.dev"`, `auth.oidc.audience = "https://tunnels.layertwo.dev"` (never empty), `auth.additionalScopes = ["HeartBeats"]`, `transport.heartbeatTimeout = 90`.
- Every frp client config: `transport.protocol = "wss"`, `transport.heartbeatInterval = 30`, `auth.additionalScopes = ["HeartBeats"]`, and `transport.tls.trustedCaFile` set. frpc skips certificate verification when it is unset.
- Pods: uid/gid `65532`, `runAsNonRoot`, `readOnlyRootFilesystem`, all capabilities dropped, no privilege escalation, seccomp `RuntimeDefault`, no service-account token, emptyDir on `/tmp`.
- IngressRoutes use class `external` (the OIDC plugin is registered only there). DNS annotations and the per-route TLS secret follow `cloud/garage/ingressroute.yml`. Issuer is ClusterIssuer `letsencrypt-prod-dns`.
- Pocket ID names: API resource `https://tunnels.layertwo.dev`; groups `tunnel-creators`, `tunnel-viewers`; clients `tunnels-gate` (confidential, authorization code with PKCE) and `tunnels-m2m-<name>` (confidential, client access to the API).
- Secrets exist only as SOPS files `secrets-*.sops.yml`, encrypted with `sops -e -i`. Never commit plaintext. Client secrets and the frpc config stay outside git.
- Branch `feat/tunnels-phase0` from `origin/mainline`; Flux tracks `mainline` only. Commit style `feat(tunnels): ...`, `docs: ...`. The design and plan documents are committed on branch `docs/tunnels-design` (a draft PR) and stay there: read them from a second worktree (`git worktree add ../homelab-docs docs/tunnels-design`), and make Task 4's results edit and commit in that worktree, never on the work branch.
- The cluster is not reachable from the design machine. Steps marked **(cluster)** need a machine on the LAN with `kubectl` access. This machine has the `sops` public recipient but not the age private key, so `sops -e` works and `sops -d` does not; verify decryption on the cluster.

**Local tools:** `kubectl`, `helm`, `sops`, `jq`, `curl`, `dig`, `openssl`, `gh`, `podman` (or `docker`), `python3` with PyYAML.

## Review Focus

1. A Pocket ID user in neither group opens a site: Pocket ID must refuse them ("You are not allowed to access this service") and nothing may reach the app. Pinned by check C5.
2. An unauthenticated visitor requests a hostname with no tunnel: they must get the login redirect (302 for an HTML request, 401 otherwise), never a 404, so nothing is revealed before login. Pinned by C6.
3. The gate's session cookie must not reach the creator's app. Pinned by C4.
4. A client with a CA bundle that does not contain the server's CA must refuse to connect, proving verification is on; one with no bundle connects unverified. Pinned by C7.
5. A tunnel whose token expires without refresh must end within about 90 seconds of `exp`. Pinned by C9.

## File Structure

| Path | Responsibility |
|------|----------------|
| `clusters/home/apps/network/tunnels/namespace.yml` | Namespace `tunnels` |
| `clusters/home/apps/network/tunnels/kustomization.yml` | Aggregates namespace, `frps/`, `routes/`, `networkpolicy.yml` |
| `clusters/home/apps/network/tunnels/frps/configmap.yml` | `frps.toml` (no secrets) |
| `clusters/home/apps/network/tunnels/frps/release.yml` | HelmRelease `frps`: Deployment, Service `frps` (ports `control` 7000, `vhost` 8080) |
| `clusters/home/apps/network/tunnels/frps/kustomization.yml` | Lists the two frps files |
| `clusters/home/apps/network/tunnels/networkpolicy.yml` | Ingress from Traefik only; egress to DNS and TCP 443 |
| `clusters/home/apps/network/tunnels/routes/secrets-oidc.sops.yml` | Secret `secrets-tunnels-oidc`: `pluginSecret`, `clientId`, `clientSecret` |
| `clusters/home/apps/network/tunnels/routes/certificate.yml` | Certificate `tunnels-sites` for `*.w.tunnels.layertwo.dev` |
| `clusters/home/apps/network/tunnels/routes/middlewares.yml` | `tunnels-oidc`, `tunnels-ratelimit`, `tunnels-inflight` |
| `clusters/home/apps/network/tunnels/routes/ingressroute-apex.yml` | `tunnels.layertwo.dev/~!frp` to frps |
| `clusters/home/apps/network/tunnels/routes/ingressroute-sites.yml` | `*.w.tunnels.layertwo.dev` through the gate to frps |
| `clusters/home/apps/network/tunnels/routes/kustomization.yml` | Lists the routes files |
| `docs/tunnels.md`, `docs/README.md` | Onboarding and limits; one index line |

Three pull requests: PR 1 = Tasks 1-2 (nothing public). PR 2 = Task 3 (public exposure). PR 3 = Tasks 4-5 (recorded results and docs). Each PR waits for the `flux-diff` comment, which shows the rendered diff, before merging; Flux reconciles within ten minutes of a merge.

---

### Task 1: Namespace, Pocket ID objects, OIDC secret

> **Moved:** the Secret file and `routes/kustomization.yml` are created in Task 3 (PR 2), because the Secret needs the `tunnels-gate` client that only exists after the manual Pocket ID step. PR 1 carries the namespace only. See Execution Notes.

**Files:**
- Create: `clusters/home/apps/network/tunnels/namespace.yml`, `kustomization.yml`, `routes/kustomization.yml`, `routes/secrets-oidc.sops.yml`

**Interfaces:**
- Produces: Namespace `tunnels` (label `goldilocks.fairwinds.com/enabled: "true"`); Secret `secrets-tunnels-oidc` with keys `pluginSecret`, `clientId`, `clientSecret`, which Task 3 references as `urn:k8s:secret:secrets-tunnels-oidc:<key>`; machine client credentials exported as `TUNNELS_CLIENT_ID` and `TUNNELS_CLIENT_SECRET` in a 0600 env file outside the repo, used by Tasks 4 and 5.

- [ ] **Step 1: Branch and failing check.** `git fetch origin mainline && git switch --no-track -c feat/tunnels-phase0 origin/mainline`. **(cluster)** `kubectl get namespace tunnels` fails with `NotFound`.
- [ ] **Step 2: Create the Pocket ID objects (manual, UI).** API "Tunnels" with resource `https://tunnels.layertwo.dev` (no permission keys). Groups `tunnel-creators` and `tunnel-viewers`; add your user to `tunnel-viewers`. Client `tunnels-gate`: confidential, callback `https://*.w.tunnels.layertwo.dev/oidc/callback`, PKCE on, allowed groups `tunnel-viewers` and `tunnel-creators`. Client `tunnels-m2m-test`: confidential, API access to Tunnels as **Client access (M2M)**, callback URL any placeholder. Machine clients are not subject to group checks, so in this phase an issued client is the creator credential.
- [ ] **Step 3: Verify the machine client.** Run the command below with the client's id and secret in the environment. Expected output: `['https://tunnels.layertwo.dev']`. (Cloudflare answers 403 to Python's default User-Agent on idp.layertwo.dev; curl is fine.)
  ```bash
  curl -s -d grant_type=client_credentials -d client_id="$TUNNELS_CLIENT_ID" -d client_secret="$TUNNELS_CLIENT_SECRET" \
    -d resource=https://tunnels.layertwo.dev https://idp.layertwo.dev/api/oidc/token | jq -r .access_token \
    | python3 -c "import sys,json,base64;t=sys.stdin.read().split('.')[1];print(json.loads(base64.urlsafe_b64decode(t+'='*(-len(t)%4)))['aud'])"
  ```
- [ ] **Step 4: Write the manifests.** `namespace.yml` copies `cloud/kirocrew/namespace.yml` with name `tunnels`. `kustomization.yml` lists `namespace.yml` and `routes/`; `routes/kustomization.yml` lists `secrets-oidc.sops.yml`. The Secret file is `type: Opaque`, name `secrets-tunnels-oidc`, namespace `tunnels`, `stringData` keys `pluginSecret` (exactly 32 characters: `openssl rand -hex 16`), `clientId` and `clientSecret` (from `tunnels-gate`).
- [ ] **Step 5: Encrypt and check.** `sops -e -i clusters/home/apps/network/tunnels/routes/secrets-oidc.sops.yml`. Then `grep -c 'ENC\[AES256_GCM' <file>` prints `3` or more, `grep -E '^\s+(pluginSecret|clientId|clientSecret): [^E]' <file>` prints nothing, and `kubectl kustomize clusters/home/apps/network/tunnels | grep -E '^kind:'` lists `Namespace` and `Secret`.
- [ ] **Step 6: Commit.** `git add clusters/home/apps/network/tunnels && git commit -m "feat(tunnels): add namespace and OIDC gate secret"`.

### Task 2: frps workload and NetworkPolicy

**Files:**
- Create: `frps/configmap.yml`, `frps/release.yml`, `frps/kustomization.yml`, `networkpolicy.yml` (all under `clusters/home/apps/network/tunnels/`)
- Modify: `kustomization.yml` (add `frps/` and `networkpolicy.yml`)

**Interfaces:**
- Consumes: Namespace `tunnels` (Task 1).
- Produces: Service `frps` with named ports `control` (7000) and `vhost` (8080), pod label `app.kubernetes.io/instance: frps`, ConfigMap `frps-config` with key `frps.toml`. Task 3 routes to the two ports by name.

- [ ] **Step 1: Failing check. (cluster)** `kubectl -n tunnels get deploy frps` fails with `NotFound`.
- [ ] **Step 2: Write `frps/configmap.yml`.** ConfigMap `frps-config`, key `frps.toml`:
  ```toml
  bindPort = 7000
  vhostHTTPPort = 8080
  subDomainHost = "w.tunnels.layertwo.dev"
  auth.method = "oidc"
  auth.oidc.issuer = "https://idp.layertwo.dev"
  auth.oidc.audience = "https://tunnels.layertwo.dev"
  auth.additionalScopes = ["HeartBeats"]
  transport.heartbeatTimeout = 90
  allowPorts = [{ single = 7000 }]   # 7000 is frps' own listener: no TCP proxy can ever bind it (was single = 1, see Execution Notes)
  log.to = "console"
  log.level = "info"
  ```
- [ ] **Step 3: Write `frps/release.yml`.** HelmRelease `frps` in `tunnels`, structure copied from `cloud/kirocrew/release.yml` (chart block, install/upgrade remediation), `interval: 5m`. Values: `defaultPodOptions` with `annotations: {reloader.stakater.com/auto: "true"}`, `automountServiceAccountToken: false` and `securityContext: {runAsNonRoot: true, runAsUser: 65532, runAsGroup: 65532, seccompProfile: {type: RuntimeDefault}}`; controller `main` (deployment, 1 replica) with container `frps` using the pinned image from Global Constraints (`repository`, `tag: v0.71.0@sha256:...`), `args: ["-c", "/etc/frp/frps.toml"]`, `tcpSocket` liveness and readiness probes on 7000, requests `20m`/`32Mi` and memory limit `256Mi`, container `securityContext` `{allowPrivilegeEscalation: false, readOnlyRootFilesystem: true, capabilities: {drop: ["ALL"]}}`; `service.main` with ports `control` 7000 (TCP) and `vhost` 8080 (HTTP); `persistence` `config` (type `configMap`, name `frps-config`, mounted read-only at `/etc/frp`) and `tmp` (emptyDir at `/tmp`). `frps/kustomization.yml` lists `configmap.yml` and `release.yml`.
- [ ] **Step 4: Write `networkpolicy.yml`.** Modeled on `development/forgejo/app/networkpolicy.yml`: name `frps`, selects `app.kubernetes.io/instance: frps`, policy types Ingress and Egress. Ingress: from namespace `traefik-system` (`kubernetes.io/metadata.name`) on TCP 7000 and 8080. Egress: DNS (53 UDP/TCP) and TCP 443 (Pocket ID discovery and keys).
- [ ] **Step 5: Render locally.** Extract `spec.values` with PyYAML into `/tmp/frps-values.yaml`, then `helm template frps app-template --repo https://bjw-s-labs.github.io/helm-charts --version 5.2.1 --namespace tunnels -f /tmp/frps-values.yaml > /tmp/frps-rendered.yaml`. Expected in the output: `runAsNonRoot: true`, `runAsUser: 65532`, `readOnlyRootFilesystem: true`, `automountServiceAccountToken: false`, the image digest, `mountPath: /etc/frp`, Service `targetPort: 7000` and `8080` (app-template 5.2.1 renders no `containerPort`), and the label `app.kubernetes.io/instance: frps`. If `automountServiceAccountToken` is missing, move it to `controllers.main.pod`. Also `kubectl kustomize clusters/home/apps/network/tunnels | grep -E '^kind:'` lists `ConfigMap`, `HelmRelease`, `NetworkPolicy`.
- [ ] **Step 6: Commit, open PR 1, merge.** `git add clusters/home/apps/network/tunnels && git commit -m "feat(tunnels): add frps and network policy"`; push and open a PR; read the `flux-diff` comment; merge.
- [ ] **Step 7: Verify. (cluster)** `kubectl -n tunnels get helmrelease frps` shows `Ready True`; `kubectl -n tunnels rollout status deploy/frps` succeeds; `kubectl -n tunnels logs deploy/frps` shows frps listening on 7000 and the http service on 8080 with no errors; `kubectl -n tunnels exec deploy/frps -- id -u` prints `65532`; `kubectl -n tunnels get secret secrets-tunnels-oidc -o json | jq -r '.data | keys[]'` lists the three keys (proves Flux decrypted it). Isolation: `kubectl -n default run np-test --rm -it --restart=Never --image=ghcr.io/home-operations/busybox:1.37.0 -- nc -zv -w 3 frps.tunnels.svc.cluster.local 7000` times out.

### Task 3: Public routes, certificate and gate

**Files:**
- Create: `routes/certificate.yml`, `routes/middlewares.yml`, `routes/ingressroute-apex.yml`, `routes/ingressroute-sites.yml`
- Modify: `routes/kustomization.yml` (add the four files)

**Interfaces:**
- Consumes: Secret `secrets-tunnels-oidc` (Task 1); Service `frps` ports `control` and `vhost` (Task 2).
- Produces: `wss://tunnels.layertwo.dev/~!frp`; sites at `https://<label>.w.tunnels.layertwo.dev` behind login; Secret `tunnels-sites-tls`; Middlewares `tunnels-oidc`, `tunnels-ratelimit`, `tunnels-inflight`.

- [ ] **Step 1: Failing check.** `dig +short tunnels.layertwo.dev @1.1.1.1` and `dig +short alice.w.tunnels.layertwo.dev @1.1.1.1` print nothing.
- [ ] **Step 2: Write `certificate.yml`.** Certificate `tunnels-sites` in `tunnels`: `secretName: tunnels-sites-tls`, `dnsNames: ["*.w.tunnels.layertwo.dev"]`, `issuerRef` ClusterIssuer `letsencrypt-prod-dns` (copy the shape from `cloud/garage/cert.yml`).
- [ ] **Step 3: Write `middlewares.yml`.** `tunnels-oidc` (`spec.plugin.oidc`, shape of `cloud/send/app/oidc.yml`):
  ```yaml
  Secret: "urn:k8s:secret:secrets-tunnels-oidc:pluginSecret"
  Provider:
    Url: "https://idp.layertwo.dev/"
    ClientId: "urn:k8s:secret:secrets-tunnels-oidc:clientId"
    ClientSecret: "urn:k8s:secret:secrets-tunnels-oidc:clientSecret"
    UsePkce: true
  Scopes: ["openid", "profile", "groups"]
  CookieNamePrefix: "__Secure-tunnels"   # not __Host-: with PKCE it breaks login on plugin v0.21.0 (see Execution Notes)
  Authorization:
    CheckOnEveryRequest: true    # else groups are checked once at login and cached while tokens renew silently
    AssertClaims:
      - Name: groups
        AnyOf: ["tunnel-viewers", "tunnel-creators"]
  Headers:                       # phase 0 only: lets check C4 see the claim templating; phase 1 strips these before the app
    - Name: X-Tunnels-Sub
      Value: "{{ .claims.sub }}"
    - Name: X-Tunnels-User
      Value: "{{ .claims.preferred_username }}"
    - Name: X-Tunnels-Groups
      Values: "{{ .claims.groups | mapToJsonArray }}"   # Values must render a JSON array; use the plugin docs' Header example if this syntax differs
  ```
  `tunnels-ratelimit`: `rateLimit` with `average: 50`, `burst: 100`, `period: 1s`, `sourceCriterion.requestHost: true`. `tunnels-inflight`: `inFlightReq` with `amount: 100`, `sourceCriterion.requestHost: true`.
- [ ] **Step 4: Write the IngressRoutes.** Apex: name `tunnels-apex`, annotations `external-dns.kubernetes.io/hostname: "tunnels.layertwo.dev"`, `external-dns.kubernetes.io/target: "proxy-external.layertwo.dev"`, `layertwo.dev/publish: "all"`, `kubernetes.io/ingress.class: external`; entry point `websecure`; one route ``Host(`tunnels.layertwo.dev`) && PathPrefix(`/~!frp`)`` to service `frps` port `control`; no `tls` block (the default store's `*.layertwo.dev` certificate covers it). Sites: name `tunnels-sites`, annotations hostname `"*.w.tunnels.layertwo.dev"`, the same target, `external-dns.kubernetes.io/cloudflare-proxied: "false"`, `layertwo.dev/publish: "external"`, class `external`; one route ``HostRegexp(`^[a-z0-9-]+\.w\.tunnels\.layertwo\.dev$`)`` with middlewares `tunnels-oidc`, `tunnels-ratelimit`, `tunnels-inflight` in that order, service `frps` port `vhost`; `tls.secretName: tunnels-sites-tls`.
- [ ] **Step 5: Render check.** `kubectl kustomize clusters/home/apps/network/tunnels | grep -E '^kind:|^  name:'` lists `Certificate`, three `Middleware`, two `IngressRoute`. Confirm no Secret value or client id appears in plaintext in the diff.
- [ ] **Step 6: Commit, open PR 2, merge.** `git commit -m "feat(tunnels): expose frps and gate sites with Pocket ID"`.
- [ ] **Step 7: Verify. (cluster)** `kubectl -n tunnels get certificate tunnels-sites` shows `READY True` (DNS-01 can take a few minutes). From anywhere: `dig +short tunnels.layertwo.dev @1.1.1.1` returns Cloudflare addresses; `dig +short alice.w.tunnels.layertwo.dev @1.1.1.1` returns your origin address (same as `send.layertwo.dev`); `curl -sI https://tunnels.layertwo.dev/` returns 404 (no route for `/`); `curl -sI -H 'Accept: text/html' https://alice.w.tunnels.layertwo.dev/` returns 302 to `idp.layertwo.dev` (the plugin's `Auto` mode redirects HTML requests; without the header it answers 401); `openssl s_client -connect alice.w.tunnels.layertwo.dev:443 -servername alice.w.tunnels.layertwo.dev </dev/null 2>/dev/null | openssl x509 -noout -ext subjectAltName` shows `DNS:*.w.tunnels.layertwo.dev`.

### Task 4: Verification matrix and recorded results

**Files:**
- Modify: `docs/plans/2026-10-07-tunnels-design.md` (append `## Phase 0 Results`)

**Interfaces:**
- Consumes: the deployed stack (Tasks 1-3), `TUNNELS_CLIENT_ID`/`TUNNELS_CLIENT_SECRET`, a second Pocket ID user in neither group.
- Produces: a results table (check, PASS/FAIL, note) and a list of decisions that change plans 2-4.

- [ ] **Step 1: Test client setup.** In `$CFG` create `frpc.toml` (values from Global Constraints; `user` is the proxy-name prefix):
  ```toml
  serverAddr = "tunnels.layertwo.dev"
  serverPort = 443
  user = "alice"
  transport.protocol = "wss"
  transport.heartbeatInterval = 30
  transport.tls.trustedCaFile = "/etc/ssl/certs/ca-certificates.crt"
  auth.method = "oidc"
  auth.additionalScopes = ["HeartBeats"]
  auth.oidc.clientID = "{{ .Envs.TUNNELS_CLIENT_ID }}"
  auth.oidc.clientSecret = "{{ .Envs.TUNNELS_CLIENT_SECRET }}"
  auth.oidc.tokenEndpointURL = "https://idp.layertwo.dev/api/oidc/token"
  auth.oidc.additionalEndpointParams.resource = "https://tunnels.layertwo.dev"

  [[proxies]]
  name = "default"
  type = "http"
  localIP = "echo"
  localPort = 80
  subdomain = "alice"
  ```
  Start an HTTP and WebSocket echo server and the client on one Podman network (`ghcr.io/traefik/whoami:v1.12.0` listens on port 80, returns the request headers as JSON at `/api` and echoes WebSocket messages at `/echo`): `podman network create tunnels-test`, then `podman run -d --rm --name echo --network tunnels-test ghcr.io/traefik/whoami:v1.12.0`, then `podman run -d --rm --name frpc --network tunnels-test -v "$CFG:/cfg:ro" -e TUNNELS_CLIENT_ID -e TUNNELS_CLIENT_SECRET <frpc image from Global Constraints> -c /cfg/frpc.toml`. `podman logs frpc` shows `login to server success` and `start proxy success`; `kubectl -n tunnels logs deploy/frps` **(cluster)** shows the login. The frpc image contains `/etc/ssl/certs/ca-certificates.crt` (checked); a native frpc on macOS uses `/etc/ssl/cert.pem` instead.
- [ ] **Step 2: Run each check and record it.**

  | ID | Check | Expected |
  |----|-------|----------|
  | C1 | wss through Cloudflare and Traefik: leave the client up for 70+ minutes | still connected after the first token expiry; `podman logs frpc \| grep -c 'login to server success'` is `1` |
  | C2 | DNS and certificate (Task 3 Step 7 commands) | as listed there |
  | C3 | Private browser window, `https://alice.w.tunnels.layertwo.dev` | Pocket ID login, then the echo page; then `https://bob.w.tunnels.layertwo.dev` completes login with no passkey prompt and shows frps's 404 page. This proves the wildcard callback |
  | C4 | In the JSON at `/api` and a browser console `new WebSocket('wss://alice.w.tunnels.layertwo.dev/echo')` | no `__Secure-tunnels` cookie in the `Cookie` header (and the browser shows the plugin's cookies named `__Secure-tunnels.*`); `X-Tunnels-Sub` and `X-Tunnels-User` carry the claims; record how `X-Tunnels-Groups` arrives (one value per group, or joined); WebSocket receives messages |
  | C5 | Log in as the second user (neither group), and as one in an unrelated group | Pocket ID shows "You are not allowed to access this service"; no echo page |
  | C6 | `curl -sI -H 'Accept: text/html' https://nobody.w.tunnels.layertwo.dev/`, then the same without the header | 302 to `idp.layertwo.dev`, then 401; never 404 |
  | C7 | Rerun the client with `trustedCaFile` pointing at an unrelated PEM (`openssl req -x509 -newkey rsa:2048 -nodes -keyout /dev/null -subj /CN=other -days 1 -out other.pem`); then with the line removed | first run fails with `x509: certificate signed by unknown authority`; second connects (record that the default is unverified) |
  | C8 | Client using the spike's old API (`https://tunnel.layertwo.dev`) if it still exists | frps refuses with an audience error; skip if the spike API was deleted |
  | C9 | Replace the client-credentials lines with `auth.oidc.tokenSource.type = "file"` and `auth.oidc.tokenSource.file.path = "/cfg/token"`; write a fresh token to `$CFG/token` once (the Task 1 Step 3 request, saving `.access_token`); do not refresh | the tunnel ends within about 90 s after the token's `exp`; frps logs `heartbeat timeout`; the site stops answering |
  | C10 | Isolation (Task 2 Step 7) | times out from `default`; public path still works |

- [ ] **Step 3: Record results.** Append `## Phase 0 Results` to the design doc: one table row per check (PASS/FAIL and a one-line note), then a short "Changes to plans 2-4" list for every FAIL, using the fallback named in the design's Verification section.
- [ ] **Step 4: Commit.** In the docs worktree: `git add docs/plans/2026-10-07-tunnels-design.md && git commit -m "docs: record tunnels phase 0 results" && git push`.

### Task 5: Onboarding docs

**Files:**
- Create: `docs/tunnels.md`
- Modify: `docs/README.md` (one index line after Authentication)

**Interfaces:**
- Consumes: the tested `frpc.toml` from Task 4 and its results.

- [ ] **Step 1: Failing check.** `grep -c tunnels docs/README.md` prints `0`.
- [ ] **Step 2: Write `docs/tunnels.md`.** Sections: what Phase 0 is (hosts, gate groups, trust-based names); adding a tester (create a Pocket ID machine client with M2M access to the Tunnels API; put the client in the tester's environment, never in git); the tested `frpc.toml` with the CA-bundle paths for macOS (`/etc/ssl/cert.pem`), Debian/Ubuntu (`/etc/ssl/certs/ca-certificates.crt`) and the frpc container; adding a viewer (add them to `tunnel-viewers`); limits (any client holder can claim any free name, one global gate, no sharing, revocation within about an hour); link to the design doc for phases 1-3.
- [ ] **Step 3: Add the index line** to `docs/README.md`: ``- [Tunnels](tunnels.md): Self-hosted ngrok-style tunnels behind Pocket ID, reached at `*.w.tunnels.layertwo.dev` ``.
- [ ] **Step 4: Check.** `grep -c tunnels docs/README.md` prints `1` or more, and the `frpc.toml` block in the doc matches the one tested in Task 4 line for line.
- [ ] **Step 5: Commit** on `feat/tunnels-phase0`: `git add docs/tunnels.md docs/README.md && git commit -m "docs: add tunnels onboarding"`; open PR 3 with the results; merge.

## Execution Notes (2026-10-08)

Phase 0 was executed from the design machine, which has no cluster access. Done: Tasks 1-2 and the manifests of Task 3 (PR 1 = #2449, merged on 2026-10-08 as `dacd8689`; PR 2 = #2453, draft). Every step marked **(cluster)** is still open, as are Task 3's Secret, Task 4 and Task 5.

**Deviations**

1. The Secret moved from Task 1 to Task 3 (PR 2): it needs the `tunnels-gate` client id and secret, which exist only after the manual Pocket ID step. `routes/kustomization.yml` moved with it. PR 1 is "nothing public".
2. `allowPorts = [{ single = 7000 }]`. Port 1 may be bindable by a non-root process where `net.ipv4.ip_unprivileged_port_start=0`. Verified with the pinned images: TCP proxies on remote port 7000, 0 and 2222 are rejected (`port unavailable`, `no available port`, `port not allowed`); `https` and `tcpmux` are rejected (not enabled); `udp` on 7000, `stcp` and `http` with `customDomains` are accepted but unreachable (the Service and NetworkPolicy are TCP-only and Traefik routes only `*.w.tunnels.layertwo.dev`). Phase 1's plugin closes proxy types for good.
3. app-template 5.2.1 renders no `containerPort`; the Task 2 render check asserts the Service `targetPort`s instead.
4. `CookieNamePrefix` is `__Secure-tunnels`, not `__Host-tunnels` (design Verification 5). Reproduced with the real plugin: with PKCE it sets `CodeVerifier` on `Path=/oidc/callback`, browsers reject that under `__Host-`, and login never completes.
5. PR 2 was first opened stacked on PR 1 (#2451). After #2449 merged (squash), its two commits were cherry-picked onto `mainline` as #2453 and #2451 was closed: same tree, no force-push, and `flux-diff` now runs on it.
6. `Authorization.CheckOnEveryRequest: true` was added (found in review, reproduced with the harness): by default the plugin checks the groups once at login and caches the result for the session while tokens renew silently, so a viewer removed from the groups kept access. Keep `tunnels-gate` restricted to the two groups in Pocket ID as well; group names must match exactly.
7. Images come from ghcr.io, not Docker Hub. Upstream publishes `ghcr.io/fatedier/frps` and `frpc` from the same build as Docker Hub, with identical digests, so only the registry in the reference changed. The test-side echo server (`ealen/echo-server` exists only on Docker Hub) became `ghcr.io/traefik/whoami:v1.12.0` (JSON of request headers at `/api`, WebSocket echo at `/echo`) and the isolation-test pod `ghcr.io/home-operations/busybox:1.37.0`; both checked locally.

**Checked without a cluster**

- Render gate (`kubectl kustomize` + `helm template`) for every task; `frps verify`; the pinned frps image runs under the production securityContext; the proxy-type behaviour above.
- Gate harness: real Traefik v3.7.13 and traefik-oidc-auth v0.21.0 built from the PR 2 manifests, against a mock OIDC provider and a browser-like client that enforces cookie-prefix rules. 23 checks: C4 (claims arrive as headers, gate cookies stripped, spoofed identity headers overwritten, WebSocket upgrade passes), the plugin's own second line for C5 (groups empty, other or absent give 403 and the backend is never hit), C6 (302 for HTML, 401 otherwise, 404 outside the wildcard pattern), and token renewal (the session survives a silent renewal, a viewer removed from the groups gets 403 at the next renewal, a refused refresh sends the visitor back to login). The harness is not part of this plan's deliverables and lives outside the repo.

**Still needs a cluster or you**

The Pocket ID objects (Task 1 Steps 2-3) and the gate Secret; Task 2 Step 7 and Task 3 Step 7; the Task 4 checks that involve Cloudflare, real DNS and certificates, or the live Pocket ID (C1, C2, C3, Pocket ID's own refusal page in C5, C7-C10); Task 5.
