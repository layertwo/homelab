# Authentication Setup

This document provides detailed information about the authentication setup in the homelab, including Authentik as the identity provider and Vaultwarden for password management.

## Overview

Authentik is an open-source Identity Provider that provides authentication, authorization, and user management for the homelab. It serves as a central authentication system for various applications and services.

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

## Password Management with Vaultwarden

Vaultwarden is an unofficial Bitwarden server implementation that provides password management capabilities. It's deployed as a standalone service in the homelab.

### Overview

Vaultwarden allows users to securely store and manage passwords, secure notes, credit card information, and identity information. It's API-compatible with the official Bitwarden clients, allowing users to use the official Bitwarden apps and browser extensions.

### Authentication

Vaultwarden uses its own authentication system, as it does not yet support OpenID Connect (OIDC) for integration with Authentik. Users need to create separate accounts in Vaultwarden.

#### Configuration

- **URL**: vault.layertwo.dev

### Features

- **Password Management**: Securely store and manage passwords
- **Secure Notes**: Store sensitive information in secure notes
- **Credit Card Information**: Store credit card details securely
- **Identity Information**: Store identity information for form filling
- **Attachments**: Attach files to vault items
- **Two-factor Authentication**: Add an extra layer of security
- **Password Sharing**: Share passwords with other users
- **Organization Support**: Create organizations for team password management
- **API Access**: Access vault items programmatically

### Client Applications

Vaultwarden is compatible with all official Bitwarden clients:

- **Web Interface**: Available at https://vault.layertwo.dev
- **Browser Extensions**: Chrome, Firefox, Safari, Edge, etc.
- **Mobile Apps**: iOS and Android
- **Desktop Apps**: Windows, macOS, Linux

For detailed information about Vaultwarden, see the [Vaultwarden documentation](vaultwarden.md).

## Troubleshooting

### Login Issues

If users cannot log in:

1. Check that Authentik is running and accessible
2. Verify that the user account exists and is not locked
3. Check that the authentication flow is working correctly
4. Check Authentik logs for errors

### Application Integration Issues

If applications cannot integrate with Authentik:

1. Check that the application is properly configured to use Authentik
2. Verify that the application provider is correctly set up in Authentik
3. Check that the authentication flow is working correctly
4. Check Authentik and application logs for errors

### Multi-factor Authentication Issues

If multi-factor authentication is not working:

1. Check that the MFA method is properly configured
2. Verify that the user has enrolled in MFA
3. Check that the authentication flow includes the MFA stage
4. Check Authentik logs for errors
