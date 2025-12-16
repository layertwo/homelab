# Project Structure

## Top-Level Organization

```
/
├── bootstrap/          # K3S cluster bootstrap utilities
├── cloud/             # Cloud infrastructure (IaC)
├── clusters/          # Kubernetes manifests (GitOps)
├── containers/        # Custom container images
├── docs/              # Documentation
└── scripts/           # Utility scripts
```

## Bootstrap (`bootstrap/`)

K3S cluster setup and initialization:
- `bootstrap.sh`: Generated k3sup installation script
- `devices.json`: Node configuration for k3sup
- `plan.sh`: Planning script for cluster setup
- `kubeconfig`: Cluster access credentials

## Cloud Infrastructure (`cloud/`)

### CDKTF (`cloud/cdktf/`)
TypeScript-based infrastructure for Cloudflare R2 and backups:
- `lib/app.ts`: Main application entry point
- `lib/constructs/`: Reusable CDK constructs
- `lib/stacks/`: Infrastructure stacks (backup, website)
- `cdktf.out/`: Generated Terraform configurations
- `.gen/`: Generated provider bindings

### Oracle Cloud (`cloud/oracle/`)
Terraform configurations for Oracle Cloud:
- `compute-stack/`: VM instances and autoscaling
- `network-stack/`: VPC, subnets, VPN configuration

## Kubernetes Manifests (`clusters/home/`)

GitOps-managed Kubernetes resources organized by namespace:

### Structure Pattern
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

### Key Namespaces
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

### Charts (`clusters/home/charts/`)
Flux HelmRepository definitions:
- `helm/`: Helm chart repositories
- `oci/`: OCI registry repositories
- `git/`: Git-based chart sources

### Flux System (`clusters/home/flux-system/`)
Core Flux CD components:
- `gotk-components.yaml`: Flux toolkit installation
- `gotk-sync.yaml`: Git repository sync configuration

## Custom Containers (`containers/`)

### cloudflare-ddns
Python application for dynamic DNS updates:
- `src/cloudflare_ddns/`: Source code
  - `main.py`: Entry point
  - `services/`: Cloudflare API and IP detection
- `tests/`: pytest test suite with fixtures
- `pyproject.toml`: Python project configuration

### bird
BIRD routing daemon for PureLB load balancer

### mercury
(Empty directory - future container)

## Documentation (`docs/`)

Detailed component documentation:
- `README.md`: Documentation index
- `networking.md`: Network architecture
- `storage.md`: Storage configuration
- `backup-strategy.md`: Backup procedures
- `home-automation.md`: Home Assistant setup
- `media-stack.md`: Media management
- `monitoring.md`: Monitoring stack
- `authentication.md`: SSO configuration

## Naming Conventions

### Kubernetes Resources
- **HelmReleases**: `hr-<app-name>.yml` or `release.yml`
- **Secrets**: `secrets-<purpose>.sops.yml` (always encrypted)
- **IngressRoutes**: `ingressroute.yml`
- **Namespaces**: `namespace.yml`
- **Kustomizations**: `kustomization.yml`

### Applications
- Use lowercase with hyphens: `home-assistant`, `zigbee2mqtt`
- Namespace typically matches primary application name

### Secrets
- All secrets use SOPS encryption (`.sops.yml` extension)
- Configuration in `.sops.yaml` at repository root
- Common patterns:
  - `secrets-<app>-redis.sops.yml`
  - `secrets-cloudnativepg-r2.sops.yml`
  - `secrets-<app>.sops.yml`

## File Organization Patterns

### Multi-Component Apps
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

### Simple Apps
Single-component applications:
```
<app>/
├── release.yml
├── ingressroute.yml
├── kustomization.yml
└── secrets-<app>.sops.yml
```
