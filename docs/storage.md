# Homelab Storage

This document provides detailed information about the storage setup in the homelab.

## Overview

The homelab uses a combination of external NFS and iSCSI storage, both backed by a centralized TrueNAS server, to provide persistent storage for applications.

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
  - 172.31.0.40
  - 172.31.0.41

#### Features

- Quota support for volumes
- Snapshot support
- NFS v4 with noatime option
- Permissions set to 0777 with UID/GID 3001

## Storage Classes

### sunbeam-nfs-csi

- Provided by Democratic CSI
- Uses NFS protocol
- Not set as the default storage class
- Supports volume expansion
- Uses the following mount options:
  - noatime
  - nfsvers=4

### sunbeam-iscsi-csi (default)

- Provided by HPE CSI Driver / TrueNAS CSP (`csi.hpe.com`)
- Uses iSCSI block storage
- Set as the default storage class
- Backed by a centralized TrueNAS iSCSI target (not replicated across k8s nodes)
- Supports volume expansion
- RWO only

### local-path

- Provided by the k3s built-in local-path provisioner
- Uses node-local storage (RWO only)
- Used sparingly, e.g. the `hermes` app PVC

## Backup Strategy

### VolSync

The VolSync operator is installed in the cluster, but it is not currently wired up to back up any persistent volumes — there are no `ReplicationSource` or `ReplicationDestination` resources defined anywhere in the repo. No off-site PVC backups are currently running.

### CloudNative PG Backups

CloudNative PG can back up PostgreSQL databases to Cloudflare R2 storage via `barmanObjectStore`, but this is only configured for one cluster today.

#### Configuration

- **Bucket**: layertwo-dev-cloudnativepg
- **Configured clusters**: `cnpg-immich` only (30d retention)
- All other CNPG clusters (vaultwarden, forgejo, prowlarr, radarr, sonarr, bazarr, pocket-id, cloudtak, gatus) have no backup configuration

## Storage Considerations

### Performance

- Use NFS storage for applications that require high performance or large storage capacity
- Use iSCSI storage for applications that require block storage (RWO)

### Backup

- Critical databases should be backed up using CloudNative PG backups; VolSync is installed but not currently configured to back up any PVCs
- Consider the backup schedule and retention based on the importance of the data

### Monitoring

- Monitor storage usage to prevent running out of space
- Monitor backup jobs to ensure they are completing successfully

## Troubleshooting

### Volume Provisioning Issues

If volumes are not being provisioned:

1. Check that the storage class exists and is configured correctly
2. Verify that the PVC is using the correct storage class
3. Check the logs of the CSI provisioner (democratic-csi or HPE CSI driver)

### Backup Issues

If backups are failing:

1. Check that the backup credentials are correct
2. Verify that the backup destination is accessible
3. Check the logs of the backup job
