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
- **Allowed Hosts** (applied at volume-creation time only — see the troubleshooting section
  before adding a node):
  - 172.31.0.10 (node1)
  - 172.31.0.11 (node2)
  - 172.31.0.12 (node3)
  - 172.31.0.18 (node-nv1)

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

### NFS `access denied by server` on a newly added node

**Symptom:** a pod scheduled onto a new node hangs in `ContainerCreating` with
`MountVolume.SetUp failed ... mount.nfs: access denied by server`, for both democratic-csi
PVCs and hand-made shares like `/mnt/storage0/media`. Everything works on the older nodes.

**Cause:** every TrueNAS NFS share carries a host ACL, and the new node's IP is not in it.

**The trap:** adding the node to `nfs.shareAllowedHosts` in
`clusters/home/apps/kube-system/democratic-csi/release.yml` is **not sufficient**. That list
is stamped onto each export at volume-creation time and never revisited — it only affects
volumes provisioned *afterwards*. Existing shares keep whatever list was current when they
were created. Evidence from 2026-08-23: `172.31.0.41` was present in the chart values and in
only 28 of 57 live shares, split exactly along creation date.

Hand-made shares such as `/mnt/storage0/media` are not managed by democratic-csi at all and
never pick up chart changes.

**Fix:** edit the chart values *and* backfill existing shares:

```
TRUENAS_API_KEY=... ./bootstrap/fix-nfs-share-hosts.py          # dry run
TRUENAS_API_KEY=... ./bootstrap/fix-nfs-share-hosts.py --apply
```

The script reconciles every share to the `NODE_IPS` list — adding missing entries and
removing stale ones. Keep `NODE_IPS` in sync with the chart. Removing decommissioned hosts
matters: a freed address handed out by DHCP would inherit mount access to every share.

Each `PUT` triggers an export reload, so a full run takes a few minutes; existing mounts
survive it, but expect the possibility of a brief stall.

### iSCSI sessions logged in but exposing zero LUNs

**The single highest-value check in this document.** This failure took down every
`sunbeam-iscsi-csi` volume in the cluster and went unnoticed for days, because every
individual layer reports itself healthy.

**Symptoms**

- Pods stuck `Init:0/1` or `ContainerCreating` indefinitely, with
  `MountVolume.MountDevice failed ... device not found with serial <hex> or target`
- CNPG clusters stuck `Waiting for the instances to become active`; instance pods sitting in
  `Completed` — the app in front of the database goes `0/1 Running`, not `CrashLoopBackOff`
- `iscsiadm -m session` shows sessions **present and `LOGGED_IN`**
- `multipath -ll` shows far fewer maps than there are attached volumes, possibly with a
  pathless leftover map rendered as `##,##` instead of `TrueNAS,iSCSI Disk`
- TrueNAS looks completely healthy: service running, targets/extents/mappings all intact

The trap is that iSCSI login succeeding is *not* evidence that storage works. A session can
be fully logged in and expose no LUNs at all, and nothing in `iscsiadm -m session`,
`systemctl status iscsid`, or the TrueNAS UI will say so.

**Diagnose — count LUNs per session, not sessions**

```bash
for s in /sys/class/iscsi_session/session*; do
  h=$(ls -d $s/device/target*/ 2>/dev/null | head -1)
  printf "%-10s luns=%s  %s\n" "$(basename $s)" \
    "$(ls -d ${h}*:*:*:* 2>/dev/null | wc -l)" \
    "$(cat $s/targetname 2>/dev/null | sed 's/.*://')"
done
```

`luns=0` on a session whose PVC still exists is the bug. Cross-check with
`grep -c hpe.com /proc/mounts` — if that is `0` on a node running iSCSI-backed pods, all
iSCSI storage on that node is down.

**Fix**

```bash
sudo iscsiadm -m session --rescan     # non-destructive; safe to run any time
```

Run it on every affected node. LUNs appear within seconds, multipath claims them, the
kubelet's next mount retry succeeds, and pods recover **without needing to be deleted** —
CNPG restarts its own instances and runs `pg_rewind` on the replica automatically. Verify:

```bash
sudo multipath -ll | grep -c "active ready running"   # should equal the node's attached volume count
grep -c hpe.com /proc/mounts
```

**Known cause vs. still unexplained**

The *mechanism* is confirmed: sessions were established without a completed SCSI LUN scan,
so the HPE CSI driver could not find a block device matching the serial in its publish info.

The *trigger* is not established. `node.session.scan` was already `auto` in both
`iscsid.conf` and the per-node records, so the scan should have happened at login. The
likeliest explanation is that sessions re-established during a target-side interruption at a
moment when the LUN was not yet mapped, and nothing ever rescanned afterwards. **If this
recurs, capture `dmesg -T` and `journalctl -u iscsid` from around the session's login time
before rescanning** — the rescan destroys the evidence.

**Ruled out during the incident — do not re-chase these**

- *Duplicate initiator IQNs.* Fixed 2026-07-09; all nodes verified unique.
- *TrueNAS initiator-group ACLs excluding the current IQNs.* Checked via
  `GET /api/v2.0/iscsi/initiator` — all 16 targets were reachable by a current node IQN.
- *Missing or disabled extents.* 16 targets / 16 extents / 16 target-extent links, none
  disabled, no bad paths.

**Red herring: `login rejected: initiator error - target not found (02/03)`**

Nodes accumulate stale `iscsiadm` node records for long-deleted PVCs and retry them forever,
producing thousands of these per hour (3,500–7,000/hr/node was observed) and drowning out
real errors. Status class 02 detail 03 means *the target does not exist* — it is **not** an
authorization failure, so it does not indicate an ACL problem. List the strays with:

```bash
sudo iscsiadm -m node | grep -oE 'pvc-[0-9a-f-]+' | sort -u > /tmp/host-nodes.txt
kubectl get pv -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | sort -u > /tmp/live-pvs.txt
comm -23 /tmp/host-nodes.txt /tmp/live-pvs.txt
```

Anything listed refers to a PV that no longer exists and can be removed with
`sudo iscsiadm -m node -T <target-iqn> -o delete`.

**Detection gap**

Nothing alerted on this — it was found by accident. Pods wedge in `Init`/`Pending` rather
than crash-looping, so restart-count and CrashLoopBackOff alarms never fire. A cheap periodic
check on each node comparing `grep -c hpe.com /proc/mounts` against the node's expected
attached-volume count would have caught it on day one.

### Backup Issues

If backups are failing:

1. Check that the backup credentials are correct
2. Verify that the backup destination is accessible
3. Check the logs of the backup job
