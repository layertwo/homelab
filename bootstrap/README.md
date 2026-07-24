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
  --servers 3 \
  --server-k3s-extra-args "--disable=traefik,servicelb" \
  --tls-san "172.31.0.10,172.31.0.11,172.31.0.12,172.31.0.19" \
  --background \
  --ssh-key "~/.ssh/id_ed25519" > bootstrap.sh
```

`servicelb` is disabled alongside `traefik` since MetalLB is deployed in-cluster and would conflict with klipper-lb. The `--tls-san` list includes each node's IP plus `172.31.0.19`, the kube-vip control-plane VIP.

### Other utilities

- `fix-iscsi-initiator-groups.py` — re-adds current node IQNs to TrueNAS iSCSI Initiator Groups still scoped to a stale, pre-fix IQN after a node rebuild. Dry-run by default; pass `--apply` to write changes.
- `kubectl-node_shell` — a `kubectl` plugin (`kubectl node-shell <node>`) for getting an interactive shell on a node.
