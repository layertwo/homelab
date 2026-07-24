# Monitoring Stack

This document provides detailed information about the monitoring stack in the homelab.

## Overview

The monitoring stack provides health checking and status monitoring for the homelab infrastructure and applications using Gatus, along with resource-recommendation dashboards via Goldilocks.

## Architecture

The monitoring stack follows the following workflow:

1. **Gatus** performs health checks on services at regular intervals
2. Health check results are stored in a PostgreSQL database
3. The Gatus dashboard displays service status and history
4. Alerts are sent when services become unhealthy

## Components

### Gatus

Gatus is a health dashboard that checks the health of services and sends alerts when issues are detected.

#### Configuration

- **URL**: status.layertwo.dev
- **Storage**: PostgreSQL database
- **Authentication**: Dashboard login is gated behind Pocket ID OIDC (`security.oidc` in the Gatus HelmRelease, issuer `https://idp.layertwo.dev`)
- **Endpoints**:
  - Internal services
  - External services
  - APIs
- **Alerting**:
  - Pushover notifications

### Goldilocks

Goldilocks (Fairwinds) is a VPA-based dashboard that recommends CPU/memory requests and limits for workloads across the cluster.

- **URL**: goldilocks.layertwo.dev
- **Chart**: `goldilocks` v10.4.1 from the Fairwinds Helm repository
- **VPA**: enabled, used to generate the resource recommendations

## Storage

The monitoring stack uses persistent storage for data:

- **Gatus**: PostgreSQL database for storage (CloudNativePG cluster)

## Networking

- Gatus is exposed through the **external** Traefik instance at status.layertwo.dev
- Goldilocks is exposed through the **internal** Traefik instance at goldilocks.layertwo.dev

## Alerting

Gatus provides alerting capabilities to notify administrators when services become unhealthy:

### Alert Channels

- **Pushover**: Mobile notifications for service failures
- **Email**: Email notifications (if configured)
- **Webhook**: Integration with other systems (if configured)

## Dashboards

The Gatus dashboard provides visualization of service health and status:

- Service health status (up/down)
- Response time metrics
- Status history and status percentage
- Endpoint-specific details

## Maintenance

### Updating

The applications are updated automatically through Flux CD when new versions are available in the Helm repositories.

### Backup

- Gatus's PostgreSQL database (CloudNativePG cluster) has no configured backup destination at this time

## Troubleshooting

### Gatus Issues

If Gatus is not performing health checks:

1. Check that Gatus is running and accessible
2. Verify that endpoints are configured correctly
3. Check that services are reachable
4. Check Gatus logs for errors
