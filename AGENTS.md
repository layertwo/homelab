# Agent Context Documentation

This document provides comprehensive context for AI agents working with this homelab infrastructure. It consolidates product overview, project structure, and technology stack information.

---

## Product Overview

A GitOps-managed Kubernetes homelab, built on K3S and deployed with Flux CD from this repository.

### Core Purpose

Self-hosted infrastructure for:

- **Media**: Sonarr, Radarr, Bazarr, Prowlarr, qBittorrent (behind Gluetun), Jellyfin (GPU), Recyclarr
- **Photos**: Immich
- **Files**: Send (Firefox Send fork) and Nextcloud
- **Object storage**: Garage S3 (hosted as a TrueNAS app)
- **AI**: Ollama (local LLMs, GPU-accelerated on the RTX 2080) and KiroCrew (web UI for opencode agents)
- **TAK**: CloudTAK
- **Git & CI**: Forgejo (+ Actions runner)
- **Passwords**: Vaultwarden
- **Tunnels**: self-hosted ngrok-style tunnels behind Pocket ID
- **Home automation**: Home Assistant — runs on an external host; the cluster only provides a thin passthrough
- **Auth/SSO**: Pocket ID
- **Monitoring**: Gatus

### Architecture

- **Cluster**: K3S — 3 server nodes (`node1`–`node3`, 172.31.0.10–.12) plus a GPU worker (`node-nv1`, 172.31.0.18). Control-plane VIP `172.31.0.19` (kube-vip). `traefik` and `servicelb` are disabled at install; MetalLB replaces klipper-lb.
- **GitOps**: Flux CD syncs branch `mainline`. HelmReleases plus Kustomize; secrets are SOPS-encrypted.
- **Networking**: MetalLB (internal 172.31.0.20–.29, external 172.31.0.30–.39), two Traefik instances (internal/external), ExternalDNS (Cloudflare + UniFi), and a custom CoreDNS `layertwo.dev` zone.
- **Storage**: Democratic CSI → TrueNAS NFS (`sunbeam-nfs-csi`, RWX, default); HPE CSI → TrueNAS iSCSI (`sunbeam-iscsi-csi`, RWO); K3s `local-path` (Ollama models). **No Longhorn.**
- **Backups**: Cloudflare R2 (S3-compatible) via VolSync (restic) and CloudNative PG (barman).
- **Security**: SOPS + age for secrets; cert-manager (Let's Encrypt DNS-01 via Cloudflare) for TLS; Pocket ID for OIDC/SSO.

---

## Project Structure

### Top-Level Organization

```
/
├── bootstrap/   # K3S bootstrap utilities (k3sup plan, node add/rebuild)
├── clusters/    # GitOps manifests — see clusters/home
├── containers/  # Custom container images (Python)
├── docs/        # Component documentation
└── .github/     # CI workflows and Renovate config
```

### Bootstrap (`bootstrap/`)

K3S install/rebuild utilities and node-add runbooks:

- `README.md`: k3sup rebuild guide, single-node join, the etcd-learner gotcha, the new-node checklist, and the `kubectl apply`-on-Flux-managed-objects gotcha
- `devices.json`: node inventory consumed by k3sup
- `fix-nfs-share-hosts.py`: backfills node IPs onto existing TrueNAS NFS exports (dry-run by default)

### Kubernetes Manifests (`clusters/home/`)

GitOps-managed resources, grouped by namespace under `clusters/home/apps/`.

#### Flux Wiring

- `flux-system/gotk-sync.yaml`: `GitRepository` `flux-system` (branch `mainline`) and `Kustomization` `flux-system` (`path: ./clusters/home`, `prune: true`, SOPS decryption via the `sops-age` secret)
- `apps/apps.yml`: `Kustomization` `apps` (`path: ./clusters/home/apps`, `prune: true`, SOPS)
- `network/traefik/traefik-crds.yml`: `Kustomization` `traefik-api-crds` (from the `traefik-crds` GitRepository)
- `flux-system/kustomization.yaml` also bundles `gotk-components.yaml`, `notifications.yml`, and SOPS secrets

Neither `clusters/home/` nor `clusters/home/apps/` has a `kustomization.yaml`; Flux generates one by scanning each tree, so nested `kustomization.yml` files are optional (some apps rely on auto-detection).

#### Structure Pattern

```
clusters/home/apps/<namespace>/
├── namespace.yml            # Namespace definition
├── kustomization.yml        # Lists the app's resources
└── <app>/
    ├── release.yml          # HelmRelease
    ├── ingressroute.yml     # Traefik routing
    ├── secrets-*.sops.yml   # Encrypted secrets
    └── kustomization.yml
```

#### Namespaces

| Path | Contents |
|---|---|
| `cert-manager/` | cert-manager + `ClusterIssuer` `letsencrypt-prod-dns` (DNS-01 via Cloudflare) |
| `cloud/garage/` | IngressRoute/Service pointer to Garage S3 running on TrueNAS (172.31.0.8) |
| `cloud/kirocrew/` | KiroCrew web UI for opencode agents (`kiro.layertwo.dev`) |
| `cloud/nextcloud/` | Nextcloud (+ CloudNative PG Postgres, Valkey); S3 primary storage in Garage |
| `cloud/ollama/` | Ollama LLM server (GPU via `runtimeClassName: nvidia`); models PVC on `local-path` |
| `cloud/send/` | Send (Firefox Send fork) + Redis |
| `cloud/website/` | IngressRoute/redirect for `layertwo.dev`, served from Garage website |
| `database/` | CloudNative PG, MongoDB, and ScyllaDB operators |
| `development/forgejo/` | Forgejo (+ Postgres, Valkey, Actions runner with docker-in-docker) |
| `home/` | Thin passthrough (Service + IngressRoute) to an external Home Assistant host |
| `immich/` | Immich app (+ CUDA machine-learning), Postgres, Redis, VolSync |
| `kube-system/` | CoreDNS custom zone, democratic-csi, descheduler, Intel device plugin, kube-vip, node-feature-discovery, reloader, snapshot-controller, TrueNAS iSCSI CSP |
| `mediabox/` | Sonarr, Radarr, Bazarr, Prowlarr, qBittorrent (Gluetun sidecar), Jellyfin (GPU), FlareSolverr, Recyclarr (+ per-app Postgres) |
| `monitoring/` | Gatus (+ Postgres) and Goldilocks (VPA recommendations) |
| `network/` | Cloudflare DDNS, ExternalDNS (Cloudflare + UniFi), MetalLB, Traefik (internal/external), Tunnels |
| `security/` | Pocket ID (+ Postgres and `oidc-saml-bridge`), Vaultwarden |
| `system-upgrade/` | System Upgrade Controller, upgrade Plans, node Profiles |
| `tak/` | CloudTAK (+ PostGIS Postgres) |
| `volsync/` | VolSync operator + RBAC |

#### Charts (`clusters/home/charts/`)

Flux source definitions:

- `helm/`: `HelmRepository` objects (bjw-s, jetstack, traefik, cloudnative-pg, metallb, external-dns, ollama, nextcloud, valkey, vaultwarden, and others)
- `oci/`: OCI sources (forgejo, stakater)
- `git/`: Git-based chart sources (traefik-crds)

### Custom Containers (`containers/`)

Python images built and published by CI (`ghcr.io/layertwo/<name>:latest`, cosign-signed):

- **cloudflare-ddns**: setuptools project; console script `do-dns-update` updates a Cloudflare A record to the host's external IP. Source in `src/cloudflare_ddns/`, tests in `tests/`.
- **oidc-saml-bridge**: Flask app served by gunicorn; bridges Pocket ID (OIDC) to AWS IAM Identity Center (SAML). Source in `src/oidc_saml_bridge/`.
- **reticulum**: uv "deps-only" image shipping `rnsd` (Reticulum transport node) and `lxmd` (LXMF propagation node). No in-repo manifests yet.

### Documentation (`docs/`)

- `README.md`: documentation index
- `networking.md`, `storage.md`, `backup-strategy.md`, `tunnels.md`
- `media-stack.md`, `home-automation.md`, `monitoring.md`, `authentication.md`
- `plans/`: dated design/implementation plans (e.g. tunnels)

### Naming Conventions

#### Kubernetes Resources

- **HelmReleases**: `release.yml` (a few apps use named files or a `chartRef`)
- **Secrets**: `secrets-<purpose>.sops.yml` (always encrypted)
- **IngressRoutes**: `ingressroute.yml`
- **Namespaces**: `namespace.yml`
- **Kustomizations**: `kustomization.yml`

#### Applications

- Lowercase with hyphens: `home-assistant`, `zigbee2mqtt`. The directory is usually the namespace, but not always (e.g. `home/` → namespace `home-assistant`).

#### Secrets

- All secrets use SOPS encryption (`.sops.yml` extension)
- Rules live in `.sops.yaml` at the repository root (age recipient)
- Common patterns:
  - `secrets-<app>.sops.yml`
  - `secrets-<app>-redis.sops.yml`
  - `secrets-cloudnativepg-r2.sops.yml`

### File Organization Patterns

#### Multi-Component Apps

Apps with multiple components (app + database + cache):

```
<app>/
├── kustomization.yml
├── namespace.yml
├── app/
│   ├── release.yml
│   ├── ingressroute.yml
│   └── kustomization.yml
├── postgres/
│   ├── cnpg-<app>.yml
│   └── kustomization.yml
└── redis/ (or valkey/)
    ├── release.yml
    └── secrets-redis.sops.yml
```

#### Simple Apps

Single-component applications:

```
<app>/
├── release.yml
├── ingressroute.yml
├── kustomization.yml
└── secrets-<app>.sops.yml
```

---

## Technology Stack

### Core Technologies

#### Kubernetes & GitOps

- **K3S**: lightweight Kubernetes distribution
- **Flux CD**: GitOps controller (HelmRelease, Kustomization, SOPS decryption)
- **Helm** and **Kustomize**: chart packaging and manifest generation
- **k3sup**: node bootstrap

#### Languages & Runtimes

- **Python**: custom containers (setuptools or uv); container base images are Python 3.14+
- **Shell**: bootstrap scripts and container entrypoints

#### Storage & Databases

- **CloudNative PG**: PostgreSQL operator (backs most apps; those needing it back up to R2 via barman)
- **Valkey**: Redis-compatible cache
- **MongoDB** and **ScyllaDB** operators (deployed)
- **Democratic CSI** (TrueNAS NFS), **HPE CSI** (TrueNAS iSCSI), **VolSync** (PVC backup)
- **Garage**: S3-compatible object storage (external TrueNAS app)

#### Networking

- **Traefik**: internal + external ingress (`internal`/`external` IngressClasses)
- **MetalLB**: IP pools `internal` (172.31.0.20–.29) and `external` (172.31.0.30–.39)
- **ExternalDNS**: `external-dns-cloudflare` (public) and `external-dns-unifi` (internal `layertwo.dev` / `layertwo.lan`)
- **Cloudflare**: DNS, R2 storage, and DDNS
- **CoreDNS**: custom `layertwo.dev` zone (static node hosts + forward to 172.31.0.1)

Publish class is set per IngressRoute with the `layertwo.dev/publish` annotation (`internal`, `external`, or `all`).

#### Security & Secrets

- **SOPS** + age (`.sops.yml` files, `sops-age` decryption secret)
- **cert-manager**: TLS automation (`letsencrypt-prod-dns` ClusterIssuer)
- **Pocket ID**: OIDC provider (`idp.layertwo.dev`); `oidc-saml-bridge` bridges to AWS SSO

#### CI/CD & Automation

- **GitHub Actions**: build/test/publish container images (cosign-signed), CodeQL, and `flux-diff` (posts a `flate diff` on PRs touching `clusters/home/**`)
- **Renovate**: `.github/renovate.json5` + `.github/renovate/*.json5`; tracks Helm charts, container images, and GitHub Actions, including `# renovate:` annotation blocks

### Common Commands

#### Python containers (setuptools: cloudflare-ddns, oidc-saml-bridge)

```bash
cd containers/<name>
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
pytest            # 100% coverage gate
black src/ tests/ # format
isort src/ tests/ # sort imports
flake8            # lint
```

#### Python containers (uv: reticulum)

```bash
cd containers/reticulum
uv sync --locked
```

#### Kubernetes & Flux

```bash
# Flux operations
flux reconcile source git flux-system
flux reconcile kustomization apps
flux get helmreleases -A
flux logs --follow

# Validate locally before pushing
kubectl kustomize clusters/home/apps/<ns>/<app>
helm template <release> <repo>/<chart> -f <values>

# Kubernetes operations
kubectl get pods -A
kubectl logs -n <namespace> <pod>
kubectl describe helmrelease -n <namespace> <name>
```

### Development Tools

#### Python

- **pytest** with `pytest-cov` (`--cov-fail-under=100`)
- **black** (line length 100), **isort** (black profile), **flake8** (max line length 100)

### Build Artifacts

- **Container images**: `ghcr.io/layertwo/<name>` (cloudflare-ddns, oidc-saml-bridge, reticulum)
- **Python**: `.egg-info/` and `__pycache__/` directories (not committed)

---

## Conventions & Gotchas

- **Secrets are always SOPS-encrypted.** Committing plaintext secrets is a bug.
- **Flux owns cluster objects.** Prefer editing git and reconciling over `kubectl apply`; see `bootstrap/README.md` for why a client-side apply silently merges stale map keys. Prefer `helm rollback` over hand-patching a Deployment.
- **Renovate pins some images by digest** in HelmReleases; expect `# renovate:` annotations beside image refs.
- **Adding/rebuilding a node:** follow the checklist in `bootstrap/README.md` (NFS export hosts, iSCSI IQNs, CoreDNS entry, `location=home` label) or storage/networking silently misbehaves.
