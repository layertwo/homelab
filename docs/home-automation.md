# Home Automation Stack

This document provides detailed information about the home automation stack in the homelab.

## Overview

The home automation stack is a collection of applications that work together to automate and control smart home devices. The stack includes:

- **Home Assistant**: Home automation platform
- **MQTT**: Message broker for IoT devices
- **Zigbee2MQTT**: Bridge for Zigbee devices
- **Z-Wave JS UI**: Management for Z-Wave devices

## Architecture

The home automation stack follows the following workflow:

1. **Zigbee2MQTT** and **Z-Wave JS UI** connect to USB controllers to communicate with Zigbee and Z-Wave devices
2. These bridges publish device states and receive commands via **MQTT**
3. **Home Assistant** connects to MQTT to monitor and control devices
4. **Home Assistant** provides a web interface for user interaction and automation

## Components

### Home Assistant

Home Assistant is an open-source home automation platform that puts local control and privacy first. It can integrate with a wide range of smart home devices and services.

#### Configuration

- **URL**: homeassistant.layertwo.dev
- **Storage**: PVC for configuration and database
- **Integrations**:
  - MQTT
  - Zigbee2MQTT
  - Z-Wave JS

### MQTT (EMQX)

EMQX is an MQTT broker that provides a messaging infrastructure for IoT devices. It serves as the central communication hub for the home automation stack.

#### Configuration

- **URL**: mqtt.layertwo.dev
- **Storage**: PVC for data
- **Ports**:
  - 1883: MQTT
  - 8083: MQTT over WebSocket
  - 8883: MQTT over TLS
  - 8084: MQTT over WSS

### Zigbee2MQTT

Zigbee2MQTT is a bridge that connects Zigbee devices to MQTT. It allows you to control Zigbee devices without the need for proprietary hubs.

#### Configuration

- **URL**: zigbee2mqtt.layertwo.dev
- **Storage**: PVC for configuration and database
- **Hardware**: USB Zigbee controller (e.g., CC2531, CC2652R)
- **MQTT Connection**: Connects to EMQX

### Z-Wave JS UI

Z-Wave JS UI is a web interface for Z-Wave JS, which is a JavaScript implementation of the Z-Wave protocol. It allows you to control Z-Wave devices and integrate them with Home Assistant.

#### Configuration

- **URL**: zwave.layertwo.dev
- **Storage**: PVC for configuration and database
- **Hardware**: USB Z-Wave controller (e.g., Aeotec Z-Stick)
- **MQTT Connection**: Connects to EMQX

## Storage

The home automation stack uses persistent storage for configuration and data:

- **Home Assistant**: PVC for configuration, database, and media
- **MQTT**: PVC for data and logs
- **Zigbee2MQTT**: PVC for configuration and database
- **Z-Wave JS UI**: PVC for configuration and database

## Networking

The home automation stack is exposed through the internal Traefik instance:

- Each application has its own subdomain (e.g., homeassistant.layertwo.dev)
- Authentication is handled by Authentik for web interfaces
- MQTT uses its own authentication mechanism

## Hardware Requirements

The home automation stack requires specific hardware to communicate with smart home devices:

- **Zigbee Controller**: A USB Zigbee controller is required for Zigbee2MQTT
- **Z-Wave Controller**: A USB Z-Wave controller is required for Z-Wave JS UI

These controllers need to be passed through to the Kubernetes nodes where the respective pods are running. This is typically done using the `nodeSelector` and `hostPath` volume to access the USB device.

## Security Considerations

- MQTT authentication should be configured to prevent unauthorized access
- Consider using TLS for MQTT connections
- Home Assistant should be configured with strong authentication
- Sensitive information should be stored as Kubernetes secrets

## Maintenance

### Updating

The applications are updated automatically through Flux CD when new versions are available in the Helm repositories.

### Backup

- Configuration is backed up using VolSync
- Home Assistant database should be backed up regularly

## Troubleshooting

### Device Connection Issues

If devices are not connecting:

1. Check that the USB controllers are properly connected to the node
2. Verify that the controllers are passed through to the pods
3. Check the logs of Zigbee2MQTT or Z-Wave JS UI for connection errors

### MQTT Issues

If MQTT communication is not working:

1. Check that EMQX is running and accessible
2. Verify that clients can connect to MQTT
3. Check MQTT authentication settings

### Home Assistant Issues

If Home Assistant is not working:

1. Check that Home Assistant is running and accessible
2. Verify that integrations are properly configured
3. Check the Home Assistant logs for errors
