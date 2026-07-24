# Authentication Setup

This document provides detailed information about the authentication setup in the homelab.

## Overview

The homelab uses **Pocket ID** as its identity provider for SSO authentication across services.

## Components

### Pocket ID

Pocket ID is a lightweight OIDC provider that supports passkey-based authentication.

#### Configuration

- Deployed in the `pocket-id` namespace
- Provides OpenID Connect (OIDC) authentication for integrated applications
- Passkey-first authentication — no password required

## Integration

Applications integrate with Pocket ID via OAuth2/OpenID Connect. Each application is registered as an OIDC client in Pocket ID with its own client ID and redirect URIs.

### OIDC-to-SAML Bridge

The `aws-sso-saml-bridge` HelmRelease (image `ghcr.io/layertwo/oidc-saml-bridge`, deployed at `clusters/home/apps/security/pocket-id/saml-bridge/`) federates Pocket ID into AWS IAM Identity Center via SAML, allowing AWS SSO to authenticate against Pocket ID as its identity source.

### Forward-Auth Middleware for Non-OIDC Apps

Some apps without native OIDC support are instead protected by a Traefik `plugin.oidc` forward-auth Middleware (`mediabox-oidc`, defined in `clusters/home/apps/mediabox/middleware.yml`) pointed at `https://idp.layertwo.dev/`, rather than being registered as native OIDC clients. This pattern is currently used by bazarr, qbittorrent, prowlarr, radarr, and sonarr.

## Security Considerations

- Use HTTPS for all service URLs
- Regularly review registered OIDC clients
- Monitor authentication logs for suspicious activity
