# Homelab Storage

This document provides detailed information about the storage setup in the homelab.

## Overview

The homelab uses a combination of external NFS storage and distributed block storage to provide persistent storage for applications.

## Storage Components

### Democratic CSI

Democratic CSI is used to connect to a TrueNAS server for NFS storage. This provides high-performance, centralized storage for applications that require it.

#### Configuration

- **TrueNAS Server**: sunbeam.layertwo.lan
- **Dataset Parent**: storage0/kubernetes/persistent-volume/nfs/volumes
- **Snapshots Dataset Parent**: storage0/kubernetes/persistent-volume/nfs/snapshots
- **Storage Class**: sunbeam-nfs-csi
- **Allowed Hosts**:
  - 172.31.0.10 (node1)
  - 172.31.0.11 (node2)
  - 172.31.0.12 (node3)

#### Features

- Quota support for volumes
- Snapshot support
- NFS v4 with noatime option
- Permissions set to 0777 with UID/GID 3001

### Longhorn

Longhorn provides distributed block storage for Kubernetes, allowing for high availability and data replication across nodes.

#### Features

- Replicated storage across multiple nodes
- Snapshot and backup support
- Volume expansion
- Disaster recovery

## Storage Classes

### sunbeam-nfs-csi

- Provided by Democratic CSI
- Uses NFS protocol
- Not set as the default storage class
- Supports volume expansion
- Uses the following mount options:
  - noatime
  - nfsvers=4

### longhorn (default)

- Provided by Longhorn
- Uses block storage
- Set as the default storage class
- Supports volume expansion
- Replicates data across nodes for high availability

## Backup Strategy

### VolSync

VolSync is used to back up persistent volumes to Cloudflare R2 storage. This provides off-site backup for critical data.

#### Configuration

- **Bucket**: layertwo-dev-volsync
- **Schedule**: Varies by application
- **Retention**: Varies by application

### CloudNative PG Backups

CloudNative PG is configured to back up PostgreSQL databases to Cloudflare R2 storage.

#### Configuration

- **Bucket**: layertwo-dev-cloudnativepg
- **Schedule**: Varies by database
- **Retention**: Varies by database

## Storage Considerations

### Performance

- Use NFS storage for applications that require high performance or large storage capacity
- Use Longhorn storage for applications that require high availability or frequent snapshots

### Backup

- Critical data should be backed up using VolSync or CloudNative PG backups
- Consider the backup schedule and retention based on the importance of the data

### Monitoring

- Monitor storage usage to prevent running out of space
- Monitor backup jobs to ensure they are completing successfully

## Troubleshooting

### Volume Provisioning Issues

If volumes are not being provisioned:

1. Check that the storage class exists and is configured correctly
2. Verify that the PVC is using the correct storage class
3. Check the logs of the CSI provisioner or Longhorn manager

### Backup Issues

If backups are failing:

1. Check that the backup credentials are correct
2. Verify that the backup destination is accessible
3. Check the logs of the backup job
