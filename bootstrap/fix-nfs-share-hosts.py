#!/usr/bin/env python3
"""Add cluster node IPs to TrueNAS NFS shares that are missing them.

democratic-csi stamps `shareAllowedHosts` onto each NFS export at volume-creation
time and never revisits it, so adding a node to the chart values only affects
volumes provisioned afterwards. Existing shares must be backfilled — this script
does that. Also covers hand-made shares (e.g. /mnt/storage0/media) that
democratic-csi does not manage at all.

Dry-run by default; pass --apply to write changes.

Usage:
    TRUENAS_API_KEY=... ./fix-nfs-share-hosts.py          # dry run
    TRUENAS_API_KEY=... ./fix-nfs-share-hosts.py --apply  # write
"""
import json
import os
import sys
import urllib.error
import urllib.request

TRUENAS_HOST = os.environ.get("TRUENAS_HOST", "sunbeam.layertwo.dev")
API_KEY = os.environ["TRUENAS_API_KEY"]

# The exact set of hosts allowed to mount cluster NFS shares. Shares are reconciled
# TO this list: missing entries are added, stale ones removed. Keep in sync with
# `nfs.shareAllowedHosts` in clusters/home/apps/kube-system/democratic-csi/release.yml
#
# 172.31.0.40 / .41 were removed 2026-08-23 — those hosts no longer exist, and leaving
# them would hand mount access to whatever DHCP assigns those addresses next.
NODE_IPS = [
    "172.31.0.10",  # node1
    "172.31.0.11",  # node2
    "172.31.0.12",  # node3
    "172.31.0.18",  # node-nv1
]
APPLY = "--apply" in sys.argv


def api(method, path, body=None):
    req = urllib.request.Request(
        f"https://{TRUENAS_HOST}/api/v2.0{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {path} -> {e.code}: {e.read().decode()}")


shares = api("GET", "/sharing/nfs")
changed = 0
for s in shares:
    hosts = s["hosts"]
    if not hosts and not s.get("networks"):
        continue  # no ACL at all = open to everyone, leave it alone

    missing = [ip for ip in NODE_IPS if ip not in hosts]
    stale = [ip for ip in hosts if ip not in NODE_IPS]
    if not missing and not stale:
        continue

    path = s.get("path") or s.get("paths")
    delta = " ".join([f"+{ip}" for ip in missing] + [f"-{ip}" for ip in stale])
    print(f"share {s['id']} ({path}): {delta}")
    if APPLY:
        # reconcile to NODE_IPS exactly, preserving the configured order
        api("PUT", f"/sharing/nfs/id/{s['id']}", {"hosts": list(NODE_IPS)})
    changed += 1

verb = "updated" if APPLY else "need updating (dry run, re-run with --apply to write)"
print(f"\n{changed} share(s) {verb}.")
