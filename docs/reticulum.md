# Reticulum

A [Reticulum](https://reticulum.network/) presence: a **transport node** (`rnsd`) and an **LXMF
propagation node** (`lxmd`), reachable at `rns.layertwo.dev:4242`. Reticulum is not HTTP, so it
does not go through Traefik; the transport node is served directly by a MetalLB LoadBalancer on
the `external` pool. Design and rationale: [design doc](plans/2026-09-09-reticulum-design.md).

## How it works

| Piece | Where |
|---|---|
| Transport node | `rnsd`, namespace `reticulum`, listening on TCP 4242 with an IFAC-protected Backbone interface |
| Public entry point | MetalLB LoadBalancer `reticulum-lb` (`external` pool), published by external-dns as `rns.layertwo.dev` |
| LAN entry point | The same LoadBalancer IP, served by UniFi DNS (`layertwo.dev/publish: all` covers both providers) |
| Propagation node | `lxmd`, a Reticulum client that dials the `rnsd` ClusterIP and stores LXMF messages for peers that are offline |
| Identity / IFAC | Age-encrypted SOPS Secrets `secrets-rnsd` and `secrets-lxmd` |

Manifests: `clusters/home/apps/cloud/reticulum/`. Container image: `ghcr.io/layertwo/reticulum`,
built by `.github/workflows/reticulum-docker-image.yml` and pinned here by digest.

## Reaching it

Point a Reticulum client at `rns.layertwo.dev` port `4242` and give it the IFAC network name and
passphrase from `secrets-rnsd` (out of band; never in git). On the LAN the same name resolves
through UniFi DNS; from the internet it needs the router forward below.

## Operations

- **No probes and no Gatus TCP check, on purpose.** A TCP connect-and-close looks like flapping to
  the Backbone interface, which bans the source IP. `rnsd` exits on interface errors, so a kubelet
  restart covers liveness. Do not add a TCP probe or health check to these pods.
- **No PVCs.** `rnsd`'s state is a regenerable cache. `lxmd`'s message store is `emptyDir`, so
  messages queued for offline peers are lost when the pod restarts.
- **Image updates** are a digest bump in `rnsd/release.yml` and `lxmd/release.yml`; Renovate opens
  these. The digest must match what the image workflow publishes.
- **Secrets** are SOPS-encrypted with the repo age key; edit with `sops` only.

### One-time router setup

MetalLB assigns the LoadBalancer IP. Forward **TCP 4242** on the UniFi router to that IP, then
pin it in `rnsd/release.yml` with `metallb.io/loadBalancerIPs` so a Service re-create cannot move
the address the router points at.

## Troubleshooting

| Symptom | Cause |
|---|---|
| Peers cannot reach `rns.layertwo.dev:4242` from outside | The router forward is missing, or the LoadBalancer IP changed after a Service re-create and was not pinned |
| Peers connect but are rejected | IFAC network name / passphrase does not match `secrets-rnsd` |
| `rnsd` pod restarts repeatedly | It exits on interface errors (`panic_on_interface_error = yes`); check its logs and the mounted config |
| Queued LXMF messages disappear | Expected: `lxmd`'s store is `emptyDir`, not a PVC |
