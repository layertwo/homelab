# Backup Strategy

This document provides detailed information about the backup strategy implemented in the homelab.

## Overview

The homelab uses a comprehensive backup strategy to protect data and ensure recoverability in case of failures. The backup strategy includes:

- **VolSync**: For backing up persistent volumes
- **CloudNative PG Backups**: For backing up PostgreSQL databases

All backups are stored in Cloudflare R2, which is an S3-compatible object storage service.

## Backup Components

### VolSync

VolSync is used to back up persistent volumes to Cloudflare R2. It provides a Kubernetes-native way to back up and restore persistent volumes.

#### Configuration

- **Bucket**: layertwo-dev-volsync
- **Schedule**: Varies by application
- **Retention**: Varies by application
- **Encryption**: Data is encrypted at rest

#### Backed Up Applications

VolSync (the operator) is installed in the cluster, but it is not currently wired up to back up any application — there are no `ReplicationSource` or `ReplicationDestination` resources defined anywhere in the repo.

### CloudNative PG Backups

CloudNative PG is configured to back up PostgreSQL databases to Cloudflare R2. This provides database-level backups that are consistent and recoverable.

#### Configuration

- **Bucket**: layertwo-dev-cloudnativepg
- **Schedule**: Varies by database
- **Retention**: Varies by database
- **WAL Archiving**: Enabled for point-in-time recovery

#### Backed Up Databases

- Immich (the only CloudNative PG cluster currently configured with a `barmanObjectStore` backup target; other CNPG clusters in the cluster — pocket-id, vaultwarden, forgejo, bazarr, prowlarr, radarr, sonarr, cloudtak, gatus — are not currently backed up to R2)

## Backup Storage

### Cloudflare R2

Cloudflare R2 is used as the backup storage destination for all backups. It provides S3-compatible object storage with no egress fees.

#### Configuration

- **Account ID**: Configured as an environment variable
- **Access Key**: Configured as an environment variable
- **Secret Key**: Configured as an environment variable
- **Region**: WNAM (Western North America)

## Backup Schedule

Backups are scheduled at different intervals depending on the importance of the data and the frequency of changes:

- **Critical Data**: Daily backups
- **Important Data**: Weekly backups
- **Standard Data**: Monthly backups

## Retention Policy

Backup retention varies depending on the importance of the data:

- **Critical Data**: 30 days
- **Important Data**: 14 days
- **Standard Data**: 7 days

## Restoration Process

### VolSync Restoration

To restore a persistent volume using VolSync:

1. Create a new `VolumeSync` resource with the appropriate source and destination
2. Wait for the restoration to complete
3. Verify that the data has been restored correctly

### CloudNative PG Restoration

To restore a PostgreSQL database using CloudNative PG:

1. Create a new `Cluster` resource with the appropriate backup source
2. Wait for the restoration to complete
3. Verify that the database has been restored correctly

## Testing Backups

Regular backup testing is essential to ensure that backups are working correctly and can be restored when needed. The following testing schedule is recommended:

- **Critical Data**: Monthly restoration tests
- **Important Data**: Quarterly restoration tests
- **Standard Data**: Semi-annual restoration tests

## Monitoring Backups

Backup jobs should be monitored to ensure they are completing successfully. Consider implementing:

- Kubernetes job monitoring
- Alerts for backup job failures
- Regular verification of backup integrity

## Security Considerations

- Backups are encrypted at rest in Cloudflare R2
- Access to backup storage is restricted to the backup system
- Backup credentials are stored as Kubernetes secrets

## Troubleshooting

### VolSync Issues

If VolSync backups are failing:

1. Check that VolSync is running and accessible
2. Verify that the backup destination is accessible
3. Check the VolSync logs for errors

### CloudNative PG Backup Issues

If CloudNative PG backups are failing:

1. Check that CloudNative PG is running and accessible
2. Verify that the backup destination is accessible
3. Check the CloudNative PG logs for errors

### Restoration Issues

If restoration is failing:

1. Check that the backup exists and is accessible
2. Verify that the restoration process is correctly configured
3. Check the logs of the restoration process for errors
