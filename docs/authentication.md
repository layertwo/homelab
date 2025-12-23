# Authentication Setup

This document provides detailed information about the authentication setup in the homelab.

## Overview

The homelab uses two identity providers for authentication:

- **Authentik**: Full-featured open-source Identity Provider for authentication, authorization, and user management
- **Pocket ID**: Lightweight OIDC provider for simpler authentication needs

Authentik serves as the primary authentication system for most applications and services.

## Architecture

The authentication setup follows the following workflow:

1. Users access applications through their respective URLs
2. Applications redirect unauthenticated users to Authentik
3. Authentik authenticates users and redirects them back to the application
4. Applications receive user information and grant access based on the user's permissions

## Components

### Authentik

Authentik is the core component of the authentication setup. It provides user management, authentication flows, and application integrations.

#### Configuration

- **URL**: authentik.layertwo.dev
- **Storage**:
  - PostgreSQL database for user data and configuration
  - Redis for caching and session management
- **Features**:
  - Single Sign-On (SSO)
  - Multi-factor Authentication (MFA)
  - User management
  - Application integrations
  - Authorization policies

### PostgreSQL

PostgreSQL is used as the database backend for Authentik.

#### Configuration

- **Storage**: PVC for database data
- **Backup**: CloudNative PG backups to Cloudflare R2

### Redis

Redis is used for caching and session management in Authentik.

#### Configuration

- **Storage**: PVC for Redis data

### Pocket ID

Pocket ID is a lightweight OIDC provider that can be used for simpler authentication scenarios.

#### Configuration

- Deployed in the sso namespace alongside Authentik
- Provides OpenID Connect authentication

## Integration Methods

Authentik supports various integration methods for applications:

### OAuth2/OpenID Connect

- Used for modern applications that support OAuth2 or OpenID Connect
- Provides authentication and user information
- Supports token-based authentication

### SAML

- Used for applications that support SAML
- Provides authentication and user attributes
- Supports Single Sign-On

### Proxy

- Used for applications that don't support OAuth2, OpenID Connect, or SAML
- Authentik acts as a proxy in front of the application
- Provides authentication without modifying the application

## User Management

Authentik provides comprehensive user management capabilities:

- **User Creation**: Users can be created manually or through self-registration
- **Groups**: Users can be organized into groups for easier permission management
- **Roles**: Roles can be assigned to users or groups to control access
- **Permissions**: Fine-grained permissions can be defined for applications

## Multi-factor Authentication

Authentik supports various multi-factor authentication methods:

- **TOTP**: Time-based One-Time Password (e.g., Google Authenticator)
- **WebAuthn**: Security keys and biometric authentication
- **Email**: One-time codes sent via email
- **SMS**: One-time codes sent via SMS (requires additional configuration)

## Authentication Flows

Authentik uses flows to define the authentication process:

- **Default Authentication Flow**: The standard login process
- **Password Reset Flow**: The process for resetting passwords
- **Enrollment Flow**: The process for setting up multi-factor authentication
- **Invitation Flow**: The process for inviting new users

Flows can be customized to meet specific requirements.

## Security Considerations

- Use HTTPS for all Authentik and application URLs
- Enable multi-factor authentication for sensitive applications
- Regularly review user accounts and permissions
- Monitor authentication logs for suspicious activity
- Use strong password policies

## Maintenance

### Updating

Authentik is updated automatically through Flux CD when new versions are available in the Helm repository.

### Backup

- PostgreSQL database is backed up using CloudNative PG backups
- Configuration is backed up using VolSync
