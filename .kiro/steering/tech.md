# Technology Stack

## Core Technologies

### Kubernetes & GitOps
- **K3S**: Lightweight Kubernetes distribution
- **Flux CD**: GitOps controller for continuous deployment
- **Helm**: Package manager (HelmRelease resources via Flux)
- **Kustomize**: Kubernetes manifest customization

### Infrastructure as Code
- **Terraform CDK (cdktf)**: Cloud infrastructure using TypeScript
- **OpenTofu**: Open-source Terraform alternative (binary: `tofu`)
- **Terraform**: Oracle Cloud infrastructure

### Languages & Runtimes
- **TypeScript**: Cloud infrastructure (CDKTF)
- **Python**: Custom containers (cloudflare-ddns)
- **Shell**: Bootstrap scripts, container entrypoints
- **Node.js**: >=18.0 for CDKTF projects

### Storage & Databases
- **CloudNative PG**: PostgreSQL operator for Kubernetes
- **Redis**: Caching layer for applications
- **Democratic CSI**: TrueNAS NFS integration
- **Longhorn**: Distributed block storage

### Networking
- **Traefik**: Ingress controller (internal + external instances)
- **MetalLB**: Load balancer (IP pools: 172.31.0.20-29 internal, 172.31.0.30-39 external)
- **External DNS**: Automatic DNS record management
- **Cloudflare**: DNS provider and R2 storage

### Security & Secrets
- **SOPS**: Secrets encryption (`.sops.yml` files)
- **cert-manager**: TLS certificate automation
- **Authentik**: Identity provider and SSO

## Common Commands

### CDKTF (Cloud Infrastructure)
```bash
cd cloud/cdktf
npm run build              # Compile TypeScript
npm run cdk:synth          # Generate Terraform config
npm run cdk:plan           # Show planned changes
npm run cdk:apply          # Apply infrastructure changes
npm run cdk:destroy        # Destroy infrastructure
npm test                   # Run tests
```

### Python (cloudflare-ddns)
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

### Kubernetes & Flux
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

### Terraform (Oracle Cloud)
```bash
cd cloud/oracle/compute-stack
terraform init
terraform plan
terraform apply
terraform destroy
```

## Development Tools

### TypeScript/CDKTF
- **ESLint**: Linting with TypeScript support
- **Prettier**: Code formatting
- **Jest**: Testing framework
- **ts-node**: TypeScript execution

### Python
- **pytest**: Testing with 100% coverage requirement
- **black**: Code formatting (line length: 100)
- **isort**: Import sorting (black profile)
- **flake8**: Linting

## Build Artifacts

- **CDKTF**: `cdktf.out/` directory contains generated Terraform
- **TypeScript**: Compiled `.js` and `.d.ts` files in `lib/`
- **Python**: `.egg-info/` and `__pycache__/` directories
