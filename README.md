# Homelab

A GitOps-managed Kubernetes homelab built with K3S, Flux CD, and a variety of self-hosted applications.

## Overview

This repository contains the configuration for a complete homelab infrastructure based on Kubernetes. It uses a GitOps approach with Flux CD to manage deployments, ensuring that the cluster state always matches what's defined in this repository.

The homelab includes:
- Media management (Sonarr, Radarr, Jellyfin, qBittorrent, Bazarr, Prowlarr, Recyclarr)
- Home automation (Home Assistant, MQTT, Zigbee2MQTT, Z-Wave JS UI)
- Photo management (Immich)
- Cloud file sharing (Send)
- Documentation (Outline)
- Authentication/SSO (Authentik, Pocket ID)
- Monitoring (Gatus)

> **For AI Agents**: See [AGENTS.md](AGENTS.md) for comprehensive context including project structure, technology stack, and development workflows.

## Architecture

### Cluster Setup

The homelab runs on a K3S Kubernetes cluster with the following nodes:
- 3 server nodes (node1, node2, node3)

```
node1.layertwo.dev (172.31.0.10)
node2.layertwo.dev (172.31.0.11)
node3.layertwo.dev (172.31.0.12)
```

### Network Architecture

The network is managed by:
- **MetalLB**: Provides load balancing with two IP pools:
  - Internal pool: 172.31.0.20-172.31.0.29
  - External pool: 172.31.0.30-172.31.0.39

- **Traefik**: Serves as the ingress controller with two instances:
  - Internal Traefik (172.31.0.20): For internal services
  - External Traefik (172.31.0.30): For external access with TLS configuration

- **External DNS**: Automatically manages DNS records in Cloudflare

- **Cloudflare DDNS**: Custom container that updates Cloudflare DNS records with the current external IP

### Storage Architecture

Storage is provided by:
- **Democratic CSI**: Connects to a TrueNAS server (sunbeam.layertwo.lan) for NFS storage
- **Longhorn**: Distributed block storage for Kubernetes

### Backup Strategy

Backups are stored in Cloudflare R2 (S3-compatible storage) with dedicated buckets:
- `layertwo-dev-volsync`: For VolSync backups (persistent volume backups)
- `layertwo-dev-cloudnativepg`: For CloudNative PostgreSQL backups
- `layertwo-dev-tofu`: For Terraform state files

## Components

### Kubernetes Infrastructure

- **K3S**: Lightweight Kubernetes distribution
- **Flux CD**: GitOps controller that ensures the cluster state matches the repository
- **SOPS**: Secrets management with encryption
- **VolSync**: Persistent volume backup and restore
- **Democratic CSI**: CSI driver for TrueNAS NFS storage
- **Longhorn**: Distributed block storage
- **System Upgrade Controller**: Manages K3S upgrades

### Networking Components

- **Traefik**: Ingress controller with internal and external instances
- **MetalLB**: Load balancer for Kubernetes services
- **External DNS**: Automatic DNS management
- **Cloudflare DDNS**: Dynamic DNS updater

### Storage Components

- **Democratic CSI**: CSI driver for TrueNAS NFS storage
- **Longhorn**: Distributed block storage
- **CloudNative PG**: PostgreSQL operator

### Security Components

- **Cert Manager**: Automatic TLS certificate management
- **Authentik**: Identity provider and SSO solution

### Monitoring Components

- **Gatus**: Service health checking and uptime monitoring

## Applications

### Media Management

- **Sonarr**: TV show management
- **Radarr**: Movie management
- **Bazarr**: Subtitle management
- **Prowlarr**: Indexer management
- **qBittorrent**: Download client
- **Jellyfin**: Media server
- **Recyclarr**: Configuration management for *arr apps

### Home Automation

- **Home Assistant**: Home automation platform
- **MQTT**: Message broker for IoT devices
- **Zigbee2MQTT**: Bridge for Zigbee devices
- **Z-Wave JS UI**: Management for Z-Wave devices

### Photo Management

- **Immich**: Self-hosted photo and video backup solution

### Documentation

- **Outline**: Wiki and knowledge base

### Authentication

- **Authentik**: Identity provider and SSO solution
- **Pocket ID**: Lightweight OIDC provider

## Custom Containers

### cloudflare-ddns

A Python script that updates DNS records on Cloudflare dynamically. It retrieves the external IP address of the machine it's running on and updates the specified DNS record accordingly.

### bird

A packaging of the BIRD routing software for use with PureLB, a load-balancer orchestrator for Kubernetes clusters.

## Setup and Bootstrap

### K3S Installation

The bootstrap directory contains utilities for setting up the K3S cluster:

1. Install k3sup:
```bash
curl -sLS https://get.k3sup.dev | sh
sudo cp k3sup /usr/local/bin/k3sup
```

2. Create a k3sup plan using the devices.json file:
```bash
k3sup plan \
  devices.json \
  --user $USER \
  --servers 3 \
  --server-k3s-extra-args "--disable traefik" \
  --background > bootstrap.sh
```

3. Execute the bootstrap script to set up the K3S cluster.

### Flux CD Setup

After the K3S cluster is running, Flux CD is installed to manage the GitOps workflow. Flux CD synchronizes the cluster state with this repository, ensuring that all applications and configurations are deployed as defined.

## Cloud Infrastructure

### DNS Management

- **Cloudflare**: DNS management with automatic updates via External DNS and Cloudflare DDNS

## Documentation

Detailed documentation for the various components of the homelab can be found in the [docs](docs) directory:

- [Networking](docs/networking.md): Details about the networking setup
- [Storage](docs/storage.md): Information about the storage setup
- [Media Stack](docs/media-stack.md): Documentation for the media management applications
- [Home Automation](docs/home-automation.md): Details about the home automation setup
- [Monitoring](docs/monitoring.md): Information about the monitoring stack
- [Authentication](docs/authentication.md): Documentation for the authentication setup
- [Backup Strategy](docs/backup-strategy.md): Details about the backup strategy

## License

This project is licensed under the terms of the LICENSE file included in the repository.
