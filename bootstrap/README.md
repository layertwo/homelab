# Bootstrap K3S

This is a collection of utilities for bootstrapping my own K3S and allows for rebuilding in case something goes wrong

## What to do?

### k3sup

#### Install `k3sup`

```
curl -sLS https://get.k3sup.dev | sh
sudo cp k3sup /usr/local/bin/k3sup
```

#### Create k3sup plan

Because there are multiple nodes available, use `devices.json` create a plan to execute on the cluster hosts

```
k3sup plan \
  devices.json \
  --user $USER \
  --servers 4 \
  --server-k3s-extra-args "--disable=traefik,servicelb" \
  --tls-san "172.31.0.10,172.31.0.11,172.31.0.12,172.31.0.18,172.31.0.19" \
  --background \
  --ssh-key "~/.ssh/id_ed25519" > bootstrap.sh
```

`servicelb` is disabled alongside `traefik` since MetalLB is deployed in-cluster and would conflict with klipper-lb. The `--tls-san` list includes each node's IP plus `172.31.0.19`, the kube-vip control-plane VIP.

`bootstrap.sh` rebuilds the cluster from scratch — do not run it against a live cluster.

#### Joining a single node to the existing cluster

Run only the relevant `k3sup join` block from `bootstrap.sh`, and **pin the version** to
whatever the cluster is already running:

```
k3sup join --host <ip> --server-host 172.31.0.10 --server \
  --node-token "$(k3sup node-token --host 172.31.0.10 --user $USER --ssh-key ~/.ssh/id_ed25519)" \
  --user $USER \
  --k3s-version "$(kubectl get node node1.layertwo.dev -o jsonpath='{.status.nodeInfo.kubeletVersion}')" \
  --tls-san "172.31.0.10,172.31.0.11,172.31.0.12,172.31.0.18,172.31.0.19" \
  --k3s-extra-args "--disable=traefik,servicelb" \
  --ssh-key ~/.ssh/id_ed25519
```

Without `--k3s-version`, k3sup uses the `stable` channel and will happily install a k3s
*newer* than the existing servers once stable moves on.

##### Gotcha: `too many learner members in cluster`

etcd allows exactly one learner (a new, not-yet-voting member) at a time. If a join loops
forever on `Waiting for other members to finish joining etcd cluster: etcdserver: too many
learner members in cluster`, a stale member is holding the slot. This is not harmless —
the joining node retries a raft configuration change every second, which is quorum-committed
and applied cluster-wide before being rejected, driving `apply request took too long` and
`no leader` errors on the healthy nodes.

k3s no longer ships `etcdctl`, so fetch a matching one (`k3s --version` reports the etcd
version) on a healthy server:

```
ETCD_VER=v3.6.14
curl -sL https://github.com/etcd-io/etcd/releases/download/${ETCD_VER}/etcd-${ETCD_VER}-linux-amd64.tar.gz \
  | tar xz -C /tmp --strip-components=1 etcd-${ETCD_VER}-linux-amd64/etcdctl

CRT=/var/lib/rancher/k3s/server/tls/etcd
sudo /tmp/etcdctl --cacert=$CRT/server-ca.crt --cert=$CRT/client.crt --key=$CRT/client.key \
  --endpoints=https://127.0.0.1:2379 member list -w table
```

Stop the joining node's k3s first, confirm the stale entry shows `IS LEARNER: true` and that
the real members are healthy (`endpoint health --cluster`), then `member remove <id>` and
restart the join. Removing a learner cannot affect quorum — learners do not vote.

#### New-node checklist

A joining node needs these or storage/networking silently misbehaves:

- `nfs-common` installed, or `sunbeam-nfs-csi` (RWX) mounts fail
- **its IP added to every TrueNAS NFS share** via `fix-nfs-share-hosts.py`, or *all* NFS
  mounts fail with `access denied by server` — both democratic-csi volumes and hand-made
  shares like `/mnt/storage0/media`. Adding the node to `shareAllowedHosts` in the
  democratic-csi chart is **not** sufficient: that list is stamped onto each export at
  volume-creation time and never revisited, so it only affects volumes created afterwards.
  This is the single most likely thing to bite when adding a node.
- `open-iscsi` + `multipath-tools` installed, with a **unique** `/etc/iscsi/initiatorname.iscsi`
- its IQN added to the TrueNAS Initiator Groups via `fix-iscsi-initiator-groups.py`, or
  `sunbeam-iscsi-csi` volumes cannot attach
- `location=home` label, or `metallb-speaker` skips it
- an entry in `clusters/home/apps/kube-system/coredns/coredns-custom.yml`
- nothing in the cluster may hardcode a NIC name — node NICs differ (`eno1` vs `enp5s0`)

Verify storage actually works before declaring the node done — schedule a throwaway pod
pinned to it with one `sunbeam-nfs-csi` and one `sunbeam-iscsi-csi` PVC. A CSI DaemonSet pod
going `Ready` proves only that the driver registered, not that any volume can mount.

#### Gotcha: `kubectl apply` on a Flux-managed object silently merges

Flux creates objects server-side, so they carry no `kubectl.kubernetes.io/last-applied-configuration`
annotation. Client-side `kubectl apply` has no baseline to diff against and therefore **adds
map keys without removing ones you deleted** — editing a `nodeSelector` in a HelmRelease and
applying it leaves *both* the old and new keys, and the pod becomes unschedulable. kubectl
prints a warning about the missing annotation; it is easy to read past and it matters.

`kubectl apply --server-side --force-conflicts` does not fix this either, because the stale
key is owned by another field manager (kustomize-controller) and SSA will not delete fields
it does not manage. Remove the key explicitly:

```
kubectl patch helmrelease <name> -n <ns> --type=merge \
  -p '{"spec":{"values":{...{"nodeSelector":{"old.label/key":null}}}}}'
```

Better: commit to git and let Flux apply it. Only reach for `kubectl` when Flux is paused,
and prefer `helm rollback` over hand-patching a Deployment — patching creates drift
helm-controller will not reconcile away (drift detection is off by default), and deleting a
Deployment mid-upgrade wedges the release in `pending-upgrade`, which blocks all further
reconciles until rolled back.

### Other utilities

- `fix-iscsi-initiator-groups.py` — re-adds current node IQNs to TrueNAS iSCSI Initiator Groups still scoped to a stale, pre-fix IQN after a node rebuild. Dry-run by default; pass `--apply` to write changes.
- `kubectl-node_shell` — a `kubectl` plugin (`kubectl node-shell <node>`) for getting an interactive shell on a node.
