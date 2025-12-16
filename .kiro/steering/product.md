# Product Overview

This is a GitOps-managed Kubernetes homelab infrastructure built on K3S with Flux CD for continuous deployment.

## Core Purpose

Self-hosted infrastructure for:
- Media management (Sonarr, Radarr, Jellyfin, qBittorrent)
- Home automation (Home Assistant, MQTT, Zigbee2MQTT, Z-Wave JS UI)
- Photo management (Immich)
- Documentation (Outline)
- Authentication/SSO (Authentik, Pocket ID)
- Monitoring (Gatus, Prometheus, Grafana)

## Architecture

- **Cluster**: K3S Kubernetes with 3 server nodes (172.31.0.10-12)
- **GitOps**: Flux CD ensures cluster state matches repository
- **Networking**: MetalLB load balancing, dual Traefik ingress (internal/external), Cloudflare DNS
- **Storage**: Democratic CSI (TrueNAS NFS), Longhorn (distributed block storage)
- **Backups**: Cloudflare R2 (S3-compatible) via VolSync and CloudNative PG
- **Security**: SOPS for secrets encryption, cert-manager for TLS, Authentik for SSO

## Cloud Infrastructure

- **Oracle Cloud**: Additional compute nodes with autoscaling
- **Cloudflare**: DNS management, R2 storage buckets, DDNS updates
- **Infrastructure as Code**: Terraform CDK (TypeScript) and OpenTofu
