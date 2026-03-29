# Monitoring Stack

This document provides detailed information about the monitoring stack in the homelab.

## Overview

The monitoring stack provides health checking and status monitoring for the homelab infrastructure and applications using Gatus.

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
- **Endpoints**:
  - Internal services
  - External services
  - APIs
- **Alerting**:
  - Pushover notifications

## Storage

The monitoring stack uses persistent storage for data:

- **Gatus**: PostgreSQL database for storage (CloudNativePG cluster)

## Networking

The monitoring stack is exposed through the internal Traefik instance:

- Gatus is accessible at status.layertwo.dev

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

- Gatus PostgreSQL database is backed up using CloudNative PG backups to Cloudflare R2

## Troubleshooting

### Gatus Issues

If Gatus is not performing health checks:

1. Check that Gatus is running and accessible
2. Verify that endpoints are configured correctly
3. Check that services are reachable
4. Check Gatus logs for errors
