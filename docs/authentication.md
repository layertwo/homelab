# Authentication Setup

This document provides detailed information about the authentication setup in the homelab.

## Overview

The homelab uses **Pocket ID** as its identity provider for SSO authentication across services.

## Components

### Pocket ID

Pocket ID is a lightweight OIDC provider that supports passkey-based authentication.

#### Configuration

- Deployed in the `sso` namespace
- Provides OpenID Connect (OIDC) authentication for integrated applications
- Passkey-first authentication — no password required

## Integration

Applications integrate with Pocket ID via OAuth2/OpenID Connect. Each application is registered as an OIDC client in Pocket ID with its own client ID and redirect URIs.

## Security Considerations

- Use HTTPS for all service URLs
- Regularly review registered OIDC clients
- Monitor authentication logs for suspicious activity
