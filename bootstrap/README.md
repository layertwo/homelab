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
  --server-k3s-extra-args "--disable traefik" \
  --background > bootstrap.sh
```
