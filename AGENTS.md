# Agent Context Documentation

This document provides comprehensive context for AI agents working with this homelab infrastructure. It consolidates product overview, project structure, and technology stack information.

---

## Product Overview

This is a GitOps-managed Kubernetes homelab infrastructure built on K3S with Flux CD for continuous deployment.

### Core Purpose

Self-hosted infrastructure for:
- Media management (Sonarr, Radarr, Jellyfin, qBittorrent)
- Home automation (Home Assistant, MQTT, Zigbee2MQTT, Z-Wave JS UI)
- Photo management (Immich)
- Documentation (Outline)
- Authentication/SSO (Authentik, Pocket ID)
- Monitoring (Gatus, Prometheus, Grafana)

### Architecture

- **Cluster**: K3S Kubernetes with 3 server nodes (172.31.0.10-12)
- **GitOps**: Flux CD ensures cluster state matches repository
- **Networking**: MetalLB load balancing, dual Traefik ingress (internal/external), Cloudflare DNS
- **Storage**: Democratic CSI (TrueNAS NFS), Longhorn (distributed block storage)
- **Backups**: Cloudflare R2 (S3-compatible) via VolSync and CloudNative PG
- **Security**: SOPS for secrets encryption, cert-manager for TLS, Authentik for SSO

---

## Project Structure

### Top-Level Organization

```
/
├── bootstrap/          # K3S cluster bootstrap utilities
├── clusters/          # Kubernetes manifests (GitOps)
├── containers/        # Custom container images
├── docs/              # Documentation
└── scripts/           # Utility scripts
```

### Bootstrap (`bootstrap/`)

K3S cluster setup and initialization:
- `bootstrap.sh`: Generated k3sup installation script
- `devices.json`: Node configuration for k3sup
- `plan.sh`: Planning script for cluster setup
- `kubeconfig`: Cluster access credentials

### Kubernetes Manifests (`clusters/home/`)

GitOps-managed Kubernetes resources organized by namespace:

#### Structure Pattern
```
clusters/home/apps/<namespace>/
├── namespace.yml           # Namespace definition
├── kustomization.yml       # Kustomize configuration
├── <app>/
│   ├── release.yml         # HelmRelease manifest
│   ├── ingressroute.yml    # Traefik routing
│   ├── secrets-*.sops.yml  # Encrypted secrets
│   └── kustomization.yml   # App-level kustomization
```

#### Key Namespaces
- `cert-manager/`: TLS certificate management
- `kube-system/`: Core cluster services (CSI, storage, device plugins)
- `network/`: Networking (Traefik, MetalLB, External DNS, Cloudflare DDNS)
- `database/`: Database operators (CloudNative PG, EMQX)
- `monitoring/`: Monitoring stack (Gatus)
- `sso/`: Authentication (Authentik, Pocket ID)
- `mediabox/`: Media management apps
- `home/`: Home automation
- `immich/`: Photo management
- `volsync/`: Backup orchestration

#### Charts (`clusters/home/charts/`)
Flux HelmRepository definitions:
- `helm/`: Helm chart repositories
- `oci/`: OCI registry repositories
- `git/`: Git-based chart sources

#### Flux System (`clusters/home/flux-system/`)
Core Flux CD components:
- `gotk-components.yaml`: Flux toolkit installation
- `gotk-sync.yaml`: Git repository sync configuration

### Custom Containers (`containers/`)

#### cloudflare-ddns
Python application for dynamic DNS updates:
- `src/cloudflare_ddns/`: Source code
  - `main.py`: Entry point
  - `services/`: Cloudflare API and IP detection
- `tests/`: pytest test suite with fixtures
- `pyproject.toml`: Python project configuration

#### bird
BIRD routing daemon for PureLB load balancer

#### mercury
(Empty directory - future container)

### Documentation (`docs/`)

Detailed component documentation:
- `README.md`: Documentation index
- `networking.md`: Network architecture
- `storage.md`: Storage configuration
- `backup-strategy.md`: Backup procedures
- `home-automation.md`: Home Assistant setup
- `media-stack.md`: Media management
- `monitoring.md`: Monitoring stack
- `authentication.md`: SSO configuration

### Naming Conventions

#### Kubernetes Resources
- **HelmReleases**: `hr-<app-name>.yml` or `release.yml`
- **Secrets**: `secrets-<purpose>.sops.yml` (always encrypted)
- **IngressRoutes**: `ingressroute.yml`
- **Namespaces**: `namespace.yml`
- **Kustomizations**: `kustomization.yml`

#### Applications
- Use lowercase with hyphens: `home-assistant`, `zigbee2mqtt`
- Namespace typically matches primary application name

#### Secrets
- All secrets use SOPS encryption (`.sops.yml` extension)
- Configuration in `.sops.yaml` at repository root
- Common patterns:
  - `secrets-<app>-redis.sops.yml`
  - `secrets-cloudnativepg-r2.sops.yml`
  - `secrets-<app>.sops.yml`

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
└── redis/
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
- **K3S**: Lightweight Kubernetes distribution
- **Flux CD**: GitOps controller for continuous deployment
- **Helm**: Package manager (HelmRelease resources via Flux)
- **Kustomize**: Kubernetes manifest customization

#### Languages & Runtimes
- **Python**: Custom containers (cloudflare-ddns)
- **Shell**: Bootstrap scripts, container entrypoints

#### Storage & Databases
- **CloudNative PG**: PostgreSQL operator for Kubernetes
- **Redis**: Caching layer for applications
- **Democratic CSI**: TrueNAS NFS integration
- **Longhorn**: Distributed block storage

#### Networking
- **Traefik**: Ingress controller (internal + external instances)
- **MetalLB**: Load balancer (IP pools: 172.31.0.20-29 internal, 172.31.0.30-39 external)
- **External DNS**: Automatic DNS record management
- **Cloudflare**: DNS provider and R2 storage

#### Security & Secrets
- **SOPS**: Secrets encryption (`.sops.yml` files)
- **cert-manager**: TLS certificate automation
- **Authentik**: Identity provider and SSO

### Common Commands

#### Python (cloudflare-ddns)
```bash
cd containers/cloudflare-ddns
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"    # Install with dev dependencies
pytest                     # Run tests with coverage
black src/ tests/          # Format code
isort src/ tests/          # Sort imports
flake8                     # Lint code
```

#### Kubernetes & Flux
```bash
# Bootstrap cluster
cd bootstrap
./bootstrap.sh

# Flux operations
flux reconcile source git flux-system
flux reconcile kustomization apps
flux get helmreleases -A
flux logs --follow

# Kubernetes operations
kubectl get pods -A
kubectl logs -n <namespace> <pod>
kubectl describe helmrelease -n <namespace> <name>
```

### Development Tools

#### Python
- **pytest**: Testing with 100% coverage requirement
- **black**: Code formatting (line length: 100)
- **isort**: Import sorting (black profile)
- **flake8**: Linting

### Build Artifacts

- **TypeScript**: Compiled `.js` and `.d.ts` files in `lib/`
- **Python**: `.egg-info/` and `__pycache__/` directories
