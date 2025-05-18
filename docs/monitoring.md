# Monitoring Stack

This document provides detailed information about the monitoring stack in the homelab.

## Overview

The monitoring stack is a collection of applications that work together to monitor the health, performance, and availability of the homelab infrastructure and applications. The stack includes:

- **Prometheus & Grafana**: Metrics collection and visualization
- **Uptime Kuma**: Uptime monitoring
- **Gatus**: Service health checking

## Architecture

The monitoring stack follows the following workflow:

1. **Prometheus** collects metrics from various sources (nodes, Kubernetes, applications)
2. **Grafana** visualizes the metrics collected by Prometheus
3. **Uptime Kuma** performs regular checks on services to monitor their availability
4. **Gatus** performs health checks on services and sends alerts when issues are detected

## Components

### Prometheus & Grafana

Prometheus is a monitoring system and time series database, while Grafana is a visualization tool that works well with Prometheus.

#### Prometheus Configuration

- **Storage**: PVC for time series data
- **Scrape Interval**: 15s (default)
- **Retention**: 15d (default)
- **Targets**:
  - Kubernetes nodes
  - Kubernetes API server
  - Kubernetes services
  - Application-specific exporters

#### Grafana Configuration

- **URL**: grafana.layertwo.dev
- **Storage**: PVC for configuration and database
- **Data Sources**:
  - Prometheus
- **Dashboards**:
  - Node Exporter
  - Kubernetes
  - Application-specific dashboards

### Uptime Kuma

Uptime Kuma is a self-hosted monitoring tool that provides uptime monitoring for websites and services.

#### Configuration

- **URL**: uptime.layertwo.dev
- **Storage**: PVC for configuration and database
- **Monitored Services**:
  - External websites
  - Internal services
  - APIs

### Gatus

Gatus is a health dashboard that checks the health of services and sends alerts when issues are detected.

#### Configuration

- **URL**: gatus.layertwo.dev
- **Storage**: PVC for configuration
- **Endpoints**:
  - Internal services
  - External services
  - APIs
- **Alerting**:
  - Pushover notifications

## Storage

The monitoring stack uses persistent storage for configuration and data:

- **Prometheus**: PVC for time series data
- **Grafana**: PVC for configuration and database
- **Uptime Kuma**: PVC for configuration and database
- **Gatus**: PVC for configuration

## Networking

The monitoring stack is exposed through the internal Traefik instance:

- Each application has its own subdomain (e.g., grafana.layertwo.dev)
- Authentication is handled by Authentik

## Alerting

The monitoring stack provides alerting capabilities to notify administrators of issues:

- **Prometheus AlertManager**: Sends alerts based on Prometheus metrics
- **Uptime Kuma**: Sends alerts when services are down
- **Gatus**: Sends alerts when health checks fail

### Alert Channels

- **Pushover**: Mobile notifications
- **Email**: Email notifications
- **Webhook**: Integration with other systems

## Dashboards

The monitoring stack provides various dashboards for visualizing metrics and status:

- **Grafana Dashboards**:
  - Node Exporter: System metrics (CPU, memory, disk, network)
  - Kubernetes: Cluster metrics (pods, deployments, nodes)
  - Application-specific dashboards

- **Uptime Kuma Dashboard**:
  - Service uptime
  - Response time
  - Status history

- **Gatus Dashboard**:
  - Service health
  - Response time
  - Status history

## Maintenance

### Updating

The applications are updated automatically through Flux CD when new versions are available in the Helm repositories.

### Backup

- Configuration is backed up using VolSync
- Prometheus data is not backed up as it can be regenerated

### Data Retention

- Prometheus data is retained for 15 days by default
- Consider adjusting retention based on storage capacity and requirements

## Troubleshooting

### Prometheus Issues

If Prometheus is not collecting metrics:

1. Check that Prometheus is running and accessible
2. Verify that targets are configured correctly
3. Check that targets are reachable
4. Check Prometheus logs for errors

### Grafana Issues

If Grafana is not displaying metrics:

1. Check that Grafana is running and accessible
2. Verify that data sources are configured correctly
3. Check that dashboards are properly configured
4. Check Grafana logs for errors

### Uptime Kuma Issues

If Uptime Kuma is not monitoring services:

1. Check that Uptime Kuma is running and accessible
2. Verify that monitors are configured correctly
3. Check that services are reachable
4. Check Uptime Kuma logs for errors

### Gatus Issues

If Gatus is not performing health checks:

1. Check that Gatus is running and accessible
2. Verify that endpoints are configured correctly
3. Check that services are reachable
4. Check Gatus logs for errors
