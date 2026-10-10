# Tunnels Phase 1 Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Execute inline; no subagents are needed.

**Goal:** Deploy the released tunnels broker and CLI backend, replacing Phase 0's trust-based names and global visitor access with verified ownership and owner-only access.

**Architecture:** Retain direct Traefik-to-frps control and visitor routes. Add the broker for API/discovery, frps plugin decisions, and visitor forwardAuth; CNPG holds users. The broker does not proxy tunnel traffic, and the API remains JSON.

**Tech Stack:** Flux, app-template 5.2.1, tunnels v0.1.0 (frp v0.71.0), CNPG, Traefik, Pocket ID, SOPS/age.

**Spec:** `docs/plans/2026-10-07-tunnels-design.md`, including Phase 0 results and the Plan 2b deployment amendments. The released code is authoritative for Phase 1: no sharing, installer, restart loop, or authorization cache.

## Global Constraints

- Work in `.worktrees/tunnels-phase1`, branch `feat/tunnels-phase1` from `origin/mainline`; preserve the main checkout and other worktrees.
- Changes are limited to tunnels manifests, deployment verification, and tunnels documentation.
- Open a draft PR to `mainline`; the user merges. Never merge, mark ready, move tags, or force-push.
- Service `tunnels.layertwo.dev`; sites `w.tunnels.layertwo.dev`; issuer `https://idp.layertwo.dev`; API resource `https://tunnels.layertwo.dev`.
- Public CLI client ID `dbf1099c-ebad-4c97-b1da-137372140feb`; creators group `tunnels-creators`. Live device login, JWT signature/audience, userinfo, and refresh were verified on 2026-10-10.
- Broker image `ghcr.io/layertwo/tunnels-broker:v0.1.0@sha256:061d4ec49bfaf0bc5700231d9de026d75b1d5f17c767e7aa35d8bdc26da507d7`.
- frps image `ghcr.io/layertwo/tunnels-frps:v0.1.0@sha256:1cd411e9941d4e73ceb888cdb7061489d544867d53350069625546cf4c1d8992`.
- Both images have linux/amd64 and linux/arm64 manifests; frps's upstream version remains v0.71.0.
- One broker, one frps, one database instance. Reuse `ghcr.io/cloudnative-pg/postgresql:16.15`, `sunbeam-nfs-csi`, and 1Gi storage from the existing Pocket ID database pattern.
- Workloads run as uid/gid 65532, non-root, read-only root filesystem, no added capabilities or service-account token, seccomp RuntimeDefault.
- Secrets are committed only as SOPS-encrypted `.sops.yml`; no decryption of the existing OIDC gate secret is needed.
- Preserve the existing wildcard certificate, DNS annotations, browser OIDC client, and direct native frp WebSocket route.

## Review Focus

1. Spoofed or duplicated identity headers must not authorize a different owner's site; pin header stripping and forwardAuth replacement settings in the render check and live cross-user test.
2. Broker/database outage must fail closed; verify middleware order and check live denial when a dependency is unavailable.
3. Public apex routes must not expose `/plugin/` or `/authz`; use explicit API/discovery/health route matches, not a catch-all broker route.
4. Control connections require `NewWorkConns` as well as `HeartBeats`; assert both scopes and private dashboard exposure in the rendered resources.
5. CNPG-generated credentials, services, and app-template pod labels must match NetworkPolicy and env references; validate rendered resources and verify connectivity after reconciliation.

---

### Task 1: Private broker and database

**Files:** Add `broker/release.yml`, `broker/kustomization.yml`, `broker/secrets-broker.sops.yml`, `postgres/cnpg-tunnels.yml`, and `postgres/kustomization.yml` under `clusters/home/apps/network/tunnels/`; update its root `kustomization.yml`. Add `scripts/check-tunnels.py` for the security-relevant rendered-manifest checks.

**Interfaces:** Service `broker` port `http` 8080; Cluster `cnpg-tunnels`, application Secret `cnpg-tunnels-app` key `uri`; broker credentials Secret `secrets-tunnels-broker`.

- [ ] Add the render check asserting the new services, database, image digests, security settings, and environment references; run against Phase 0 and confirm it fails for missing broker/database.
- [ ] Create the database using the existing CNPG pattern, without superuser access.
- [ ] Create the broker HelmRelease with required public settings from Global Constraints; `DATABASE_URL` references `cnpg-tunnels-app/uri`.
- [ ] Set dashboard URL `http://frps:7500`, dashboard username `broker`, max tunnels 5, bandwidth `10MB`, and minimum CLI version `0.1.0` (advisory only).
- [ ] Generate plugin secret and dashboard password outside git; encrypt broker credentials with the repository age recipient. Reuse the same values in Task 2 without logging them.
- [ ] Add `/healthz` HTTP probes, resource requests/limits consistent with neighboring workloads, and reloader annotations.
- [ ] Run `kubectl kustomize clusters/home/apps/network/tunnels` and the applicable render assertions.

### Task 2: frps enforcement and private connectivity

**Files:** Update `frps/configmap.yml`, `frps/release.yml`, and `networkpolicy.yml`.

**Interfaces:** Existing `frps` control 7000 and vhost 8080 remain; add private dashboard 7500. frps calls `http://broker:8080/plugin/<secret>` with Login, NewProxy, CloseProxy.

- [ ] Extend the check for shared Secret environment references, both auth scopes, plugin operations, ConfigMap mounts, and allowed network peers; run before implementation to confirm failure.
- [ ] Preserve OIDC issuer/audience, `allowPorts`, console logging, and heartbeat timeout 90; add `NewWorkConns`, authenticated dashboard, and broker plugin.
- [ ] Keep the readable frps TOML in `frps-config`. Template the password and plugin path with `{{ .Envs.FRPS_DASHBOARD_PASSWORD }}` and `{{ .Envs.PLUGIN_SECRET }}`; inject both with `secretKeyRef` to `secrets-tunnels-broker`, reusing Task 1's credentials without a second Secret.
- [ ] Switch to the pinned released frps image and expose dashboard only through its ClusterIP service.
- [ ] Restrict frps ingress to external Traefik for 7000/8080 and broker for 7500; permit its broker plugin and DNS/HTTPS egress.
- [ ] Restrict broker ingress to external Traefik and frps; allow DNS/HTTPS, frps dashboard, and `cnpg-tunnels` PostgreSQL egress. Inspect actual rendered pod labels before selecting peers.
- [ ] Restrict database ingress to broker 5432 and CNPG operator management 8000; include database peer connectivity if needed by CNPG, without introducing an unverified database egress policy.
- [ ] Render HelmRelease workloads with app-template 5.2.1 and run the corresponding assertions. Verify the TOML template with dummy credentials and native frps, and check shared Secret encryption without displaying decrypted data.

### Task 3: Public routes, identity handling, and onboarding

**Files:** Update `routes/ingressroute-apex.yml`, `routes/ingressroute-sites.yml`, `routes/middlewares.yml`, and `docs/tunnels.md`.

**Interfaces:** Public `/~!frp` goes to frps; `/api/me`, `/.well-known/tunnels.json`, `/healthz` go to broker. Site middleware order is strip identity, OIDC, forwardAuth, strip internal identity, rate/in-flight limits.

- [ ] Extend the render check for explicit apex matches, private endpoint exclusion, exact site middleware order, identity headers, and `trustForwardHeader: false`; confirm failure before edits.
- [ ] Preserve direct `/~!frp` routing; add explicit broker routes and rate/in-flight limits on public API and control traffic. Do not publicly route `/plugin/`, `/authz`, or the dashboard.
- [ ] Clear `X-Tunnels-Sub`, `X-Tunnels-User`, `X-Tunnels-Groups`, and `X-Tunnel-User` before the OIDC gate.
- [ ] Configure forwardAuth to `http://broker:8080/authz`, with `trustForwardHeader: false` and `authResponseHeaders: [X-Tunnels-Sub, X-Tunnels-User, X-Tunnel-User]`. Traefik removes existing copies before applying the broker's response headers; the broker returns only `X-Tunnel-User`. Pin these exact settings in the render check and verify them with live spoofing tests.
- [ ] Strip `X-Tunnels-*` after authorization, preserving `X-Tunnel-User` for the app. Keep group access and existing gate cookie behavior.
- [ ] Replace Phase 0 onboarding with release verification, `tunnel login`, `tunnel up`, naming rules, owner-only access, revocation behavior, and troubleshooting. Explicitly note that old machine-client tunnels no longer pass the broker's creator checks.
- [ ] Run Kustomize, Helm rendering, `scripts/check-tunnels.py`, YAML parsing, and `git diff --check`; confirm the complete checks pass.
- [ ] Inspect status, full diff, and recent commit style; stage only intended files, commit, push, and open a draft PR. Inspect the `flux-diff` result before declaring the PR ready for review.

## After the user merges (cluster verification)

No kubectl context is currently configured. Perform these checks with working cluster access; do not claim local rendering proves reconciliation.

- [ ] Verify Flux reconciliation, broker/frps HelmReleases, CNPG readiness, shared Secret SOPS decryption, environment injection, and generated database credentials.
- [ ] Verify public discovery/API/health routes work and private plugin/authz/dashboard routes are inaccessible publicly.
- [ ] Run the released CLI: login, publish a disposable local HTTP server, open the site as its owner, and verify HTTP and WebSocket traffic plus `X-Tunnel-User` without internal identity headers/gate cookies.
- [ ] Confirm another creator and a viewer cannot open that owner's site, including spoofed identity/forwarded-host headers; confirm unknown sites do not reveal tunnel existence before authentication.
- [ ] Verify stolen-name registration fails, the dashboard works only from broker, and dependency failure cannot allow site access.
- [ ] Record results and remove disposable test processes and files. Retain the worktree only while the draft PR needs follow-up.

## Local execution record

- The isolated worktree starts at `a7c86a17`. Broker/database, frps enforcement, and public routing changes each had a failing render check before implementation, followed by a passing app-template render.
- Both released image digests resolve publicly for linux/amd64 and linux/arm64.
- Shared credentials were generated only in memory and stored in the production-recipient SOPS-encrypted broker Secret. Following review, frps uses Secret-backed environment templates in a readable ConfigMap, removing the duplicated encrypted TOML Secret. Production-key decryption remains a cluster check.
- Native upstream frps v0.71.0 verified the actual ConfigMap template. A disposable loopback test confirmed the environment-expanded dashboard password (correct accepted, wrong rejected) and plugin Login path, using dummy credentials and no production tokens.
- Chart rendering confirmed external Traefik's instance label `traefik-external-traefik-system` and CNPG operator labels in namespace `default`.
- Reloader annotations are on the Deployments, not only their Pods, so Secret changes trigger rollouts.
- Eight security-relevant manifest mutations were rejected, including removal of authorization, dashboard exposure, broad database egress, and empty-peer allow-all rules.
- No current kubectl context is configured; all cluster acceptance checkboxes above remain pending.
