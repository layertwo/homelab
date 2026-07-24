# Home Automation Stack

This document provides detailed information about the home automation stack in the homelab.

## Overview

As of mid-2026, the home automation stack was moved off-cluster to an external host (`192.168.255.50`). Kubernetes now only provides a thin passthrough for Home Assistant (Service + EndpointSlice + IngressRoute); it does not run Home Assistant itself. Zigbee2MQTT, Z-Wave JS UI, and the EMQX broker are no longer Flux-managed at all — only the EMQX Operator (no broker instance) remains deployed.

## Components

### Home Assistant

Home Assistant runs on an external host and is reached from the cluster via a manual `Service` + `EndpointSlice` pointing at `192.168.255.50:8123`, fronted by an `IngressRoute`. There is no HelmRelease, PVC, or database for Home Assistant in the cluster.

- **Path**: `clusters/home/apps/home/` (`namespace.yml`, `service.yml`, `ingressroute.yml`)
- **URL**: hass.layertwo.dev
- **Storage**: none in-cluster (configuration/database live on the external host)
- **Auth**: the IngressRoute has no auth middleware attached

### MQTT (EMQX)

Only the EMQX Operator Helm chart (`clusters/home/apps/database/emqx/release.yml`) remains deployed. There is no EMQX custom resource/broker instance defined anywhere, so there is currently no running MQTT broker, no PVC, no `mqtt.layertwo.dev` hostname, and no exposed ports.

### Zigbee2MQTT

Zigbee2MQTT has no Kubernetes manifests anymore (removed). The only surviving trace is a Gatus health check against `https://zigbee.layertwo.dev` — this is monitoring only; nothing is deployed behind it via Flux.

### Z-Wave JS UI

Z-Wave JS UI has no Kubernetes manifests anymore (removed). The only surviving trace is a Gatus health check against `https://zwave.layertwo.dev` — this is monitoring only; nothing is deployed behind it via Flux.

## Networking

- Home Assistant is exposed through the external Traefik instance at `hass.layertwo.dev`
- No auth middleware is currently attached to the Home Assistant `IngressRoute`
- MQTT, Zigbee2MQTT, and Z-Wave JS UI are not exposed from the cluster

## Hardware

A single combo USB stick — Silicon Labs HubZ Smart Home Controller (`HUSBZB-1`) — provides both Zigbee and Z-Wave connectivity. It is labeled via a `NodeFeatureRule` at `clusters/home/apps/kube-system/node-feature-discovery/rules/hubz-device.yml`, which sets `feature.node.kubernetes.io/zwave: "true"` and `feature.node.kubernetes.io/zigbee: "true"` based on USB vendor/device ID (`10c4:8a2a`). This label currently has no consumer — no workload in the cluster uses it, since the pods that would have (Zigbee2MQTT, Z-Wave JS UI) were removed.

## Maintenance

### Updating

The EMQX Operator is updated automatically through Flux CD when new versions are available in its Helm repository. Home Assistant, Zigbee2MQTT, Z-Wave JS UI, and the EMQX broker are managed on the external host, outside of Flux.

## Troubleshooting

### Home Assistant Issues

If Home Assistant is not working:

1. Check that the external host (`192.168.255.50`) is reachable and Home Assistant is running there
2. Verify the `EndpointSlice` in `clusters/home/apps/home/service.yml` still points at the correct address
3. Check the Home Assistant logs on the external host for errors

### Zigbee2MQTT / Z-Wave JS UI / MQTT

These are no longer deployed in the cluster. The Gatus checks for `zigbee.layertwo.dev` and `zwave.layertwo.dev` are monitoring-only leftovers; if they fail, it reflects the state of the external host, not any in-cluster workload.
