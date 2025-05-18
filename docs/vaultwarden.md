# Vaultwarden

This document provides detailed information about the Vaultwarden deployment in the homelab, including its configuration, features, and integration with other services.

## Overview

Vaultwarden is an unofficial Bitwarden server implementation written in Rust. It provides password management capabilities and is compatible with all Bitwarden clients. It's deployed in the homelab to provide a self-hosted password management solution.

## Architecture

The Vaultwarden deployment consists of the following components:

1. **Vaultwarden Server**: The main application that provides the Bitwarden API and web interface
2. **PostgreSQL Database**: Stores user data, vault items, and application configuration
3. **Redis**: Used for caching and WebSocket notifications

## Components

### Vaultwarden Server

The Vaultwarden server is the core component of the deployment. It provides the Bitwarden API and web interface.

#### Configuration

- **URL**: vault.layertwo.dev
- **Storage**: Persistent volume for data storage
- **Features**:
  - Password management
  - Secure notes
  - Credit card information
  - Identity information
  - Attachments
  - WebSocket notifications
  - Admin interface

### PostgreSQL

PostgreSQL is used as the database backend for Vaultwarden.

#### Configuration

- **Storage**: PVC for database data
- **Backup**: CloudNative PG backups to Cloudflare R2

### Redis

Redis is used for caching and WebSocket notifications in Vaultwarden.

#### Configuration

- **Storage**: In-memory only (no persistence)

## Features

### Password Management

Vaultwarden provides comprehensive password management capabilities:

- **Password Storage**: Securely store and manage passwords
- **Password Generator**: Generate strong, random passwords
- **Password Sharing**: Share passwords with other users (if enabled)
- **Password History**: View password history and changes

### Secure Notes

Vaultwarden allows users to store secure notes for sensitive information that doesn't fit into other categories.

### Credit Card Information

Users can store credit card details securely for easy access when making online purchases.

### Identity Information

Vaultwarden can store identity information for form filling, including:

- Name
- Address
- Email
- Phone number
- Social security number
- License number
- Passport number

### Attachments

Users can attach files to vault items, such as:

- Documents
- Images
- PDFs
- Other file types

### WebSocket Notifications

Vaultwarden uses WebSocket notifications to provide real-time updates to clients. This ensures that changes made on one device are immediately reflected on other devices.

### Admin Interface

The admin interface provides administrative capabilities:

- **User Management**: Create, edit, and delete users
- **Organization Management**: Manage organizations and collections
- **Invitation Management**: Manage user invitations
- **Statistics**: View usage statistics

## Client Applications

Vaultwarden is compatible with all official Bitwarden clients:

- **Web Interface**: Available at https://vault.layertwo.dev
- **Browser Extensions**: Chrome, Firefox, Safari, Edge, etc.
- **Mobile Apps**: iOS and Android
- **Desktop Apps**: Windows, macOS, Linux
- **CLI**: Command-line interface for scripting and automation

## Security Considerations

- **Encryption**: All data is encrypted using AES-256 encryption
- **Zero-knowledge**: The server never has access to unencrypted data
- **Two-factor Authentication**: Additional security layer (if enabled)
- **Admin Token**: Required for administrative access
- **HTTPS**: All communication is encrypted using HTTPS

## Maintenance

### Updating

Vaultwarden is updated automatically through Flux CD when new versions are available in the Docker registry.

### Backup

- PostgreSQL database is backed up using CloudNative PG backups
- Data directory is backed up using VolSync (if configured)

## Troubleshooting

### Login Issues

If users cannot log in:

1. Check that Vaultwarden is running and accessible
2. Verify that the user account exists
3. Check Vaultwarden logs for errors

### Database Issues

If there are database connection issues:

1. Check that PostgreSQL is running
2. Verify that the database connection string is correct
3. Check PostgreSQL logs for errors

### WebSocket Issues

If WebSocket notifications are not working:

1. Check that Redis is running
2. Verify that WebSocket is enabled in Vaultwarden configuration
3. Check that the WebSocket endpoint is properly exposed in the IngressRoute

## Integration with Other Services

### Authentik

Vaultwarden does not yet support OpenID Connect (OIDC) for integration with Authentik. Once OIDC support is added to Vaultwarden in a future release, it could be integrated with Authentik for Single Sign-On (SSO). For now, users need to create and manage separate accounts in Vaultwarden.

## References

- [Vaultwarden GitHub Repository](https://github.com/dani-garcia/vaultwarden)
- [Bitwarden Documentation](https://bitwarden.com/help/)
- [Vaultwarden Wiki](https://github.com/dani-garcia/vaultwarden/wiki)
