# Homelab Documentation

This directory contains detailed documentation for the various components of the homelab.

## Overview

The homelab is a GitOps-managed Kubernetes cluster built with K3S, Flux CD, and a variety of self-hosted applications. This documentation provides detailed information about the different components of the homelab.

## Documentation Structure

- [Networking](networking.md): Details about the networking setup, including MetalLB, Traefik, and DNS configuration
- [Storage](storage.md): Information about the storage setup, including Democratic CSI, Longhorn, and backup strategy
- [Media Stack](media-stack.md): Documentation for the media management applications, including Sonarr, Radarr, and Jellyfin
- [Home Automation](home-automation.md): Details about the home automation setup, including Home Assistant, MQTT, and device integration
- [Monitoring](monitoring.md): Information about the monitoring stack, including Gatus health checking
  - [Gatus PostgreSQL Backend](gatus-postgres.md): Details about the PostgreSQL backend implementation for Gatus
- [Authentication](authentication.md): Documentation for the authentication setup using Authentik
- [Vaultwarden](vaultwarden.md): Documentation for the Vaultwarden password manager deployment
- [Backup Strategy](backup-strategy.md): Details about the backup strategy, including VolSync, CloudNative PG backups, and Cloudflare R2

## Getting Started

If you're new to the homelab, start with the main [README.md](../README.md) in the root directory for an overview of the entire project. Then, explore the specific documentation for the components you're interested in.

## Contributing

If you'd like to contribute to the documentation, please follow these guidelines:

1. Use Markdown for all documentation
2. Follow the existing structure and style
3. Include detailed information about configuration, networking, storage, and troubleshooting
4. Add diagrams where appropriate to visualize complex setups

## Troubleshooting

Each component's documentation includes a troubleshooting section with common issues and solutions. If you encounter an issue that's not covered in the documentation, please consider adding it to help others in the future.
