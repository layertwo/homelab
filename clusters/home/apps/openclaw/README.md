# OpenClaw

AI assistant gateway for running agents on your homelab.

## Prerequisites

- Kubernetes cluster with Flux CD
- Traefik ingress controller
- cert-manager for TLS certificates
- Persistent storage (local-hostpath or similar)

## Configuration

1. **Gateway Token**: Set in `release.yml` or via Secret
2. **Models**: Configure in the OpenClaw UI after deployment
3. **DNS**: Automatically managed via external-dns to `openclaw.layertwo.dev`

## Installation

The OpenClaw deployment is managed by Flux CD. Once committed to the repo, Flux will automatically deploy it to the cluster.

## Access

After deployment, access OpenClaw at:
- **URL**: `https://openclaw.layertwo.dev`
- **Local**: `kubectl port-forward -n openclaw svc/openclaw 18789:18789`

## Post-Install Setup

1. Get the setup code:
   ```bash
   kubectl exec -n openclaw deployment/openclaw -- openclaw qr
   ```

2. Scan the QR code with the OpenClaw mobile app

3. Configure models via the web UI or CLI:
   ```bash
   kubectl exec -n openclaw deployment/openclaw -- openclaw config set models.providers.ollama.baseUrl https://ollama.com
   ```
