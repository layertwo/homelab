# Gatus PostgreSQL Backend

This document details the implementation of PostgreSQL as the backend storage for Gatus in the homelab environment.

## Overview

Gatus has been migrated from using a local file-based storage to a PostgreSQL database backend. This change improves reliability, enables high availability, and provides better data persistence for the monitoring service.

## Architecture Changes

### Previous Configuration
- Previously, Gatus used a PVC (Persistent Volume Claim) for configuration storage
- Data was stored locally in files

### New Configuration
- Gatus now uses a PostgreSQL database for storage
- The database is provided by a CloudNativePG cluster
- Connection details are passed to Gatus via Kubernetes secrets

## Implementation Details

### PostgreSQL Database

A dedicated PostgreSQL cluster has been set up for Gatus using CloudNativePG:

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: cnpg-gatus
  namespace: monitoring
spec:
  instances: 2                           # High availability with 2 instances
  primaryUpdateStrategy: unsupervised
  primaryUpdateMethod: switchover
  imageName: ghcr.io/cloudnative-pg/postgresql:16.9
  enableSuperuserAccess: true
  storage:
    storageClass: sunbeam-nfs-csi
    size: 1Gi                           # 1GB storage allocation
```

Key features:
- PostgreSQL 16.9
- 2 instances for high availability
- Automatic failover capability
- 1GB storage allocation
- NFS-based storage class

### Gatus Configuration

The Gatus Helm release has been updated to use PostgreSQL:

```yaml
config:
  storage:
    type: postgres
    path: "${POSTGRES_URI}"
```

The PostgreSQL connection string is provided via environment variables:

```yaml
env:
  POSTGRES_URI:
    valueFrom:
      secretKeyRef:
        name: cnpg-gatus-app
        key: uri
```

### Integration

The PostgreSQL cluster is included in the Gatus kustomization:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: monitoring
resources:
  - release.yml
  - secrets-pushover.sops.yml
  - ingressroute.yml
  - pdb.yml
  - postgres
```

## Benefits

1. **High Availability**: With a 2-instance PostgreSQL cluster, Gatus data remains available even if one database instance fails
2. **Data Persistence**: Better data durability compared to file-based storage
3. **Scalability**: Database storage can be easily scaled if needed
4. **Backup & Recovery**: Leverages CloudNativePG's backup capabilities
5. **Consistent State**: Ensures Gatus maintains consistent state across restarts

## Considerations

1. **Resource Usage**: The PostgreSQL cluster requires additional resources compared to file-based storage
2. **Complexity**: Adds database dependency to the monitoring stack
3. **Maintenance**: Requires PostgreSQL maintenance and updates

## Access

- The Gatus dashboard remains accessible at: uptime.layertwo.dev
- Database management is handled through CloudNativePG operators

## Troubleshooting

If Gatus experiences database connectivity issues:

1. Check that the PostgreSQL cluster is running:
   ```
   kubectl get pods -n monitoring -l postgresql=cnpg-gatus
   ```

2. Verify the database secret exists:
   ```
   kubectl get secret cnpg-gatus-app -n monitoring
   ```

3. Check Gatus logs for database connection errors:
   ```
   kubectl logs -n monitoring -l app.kubernetes.io/name=gatus
   ```

4. Ensure the PostgreSQL service is accessible:
   ```
   kubectl get svc -n monitoring -l postgresql=cnpg-gatus
   ```
