# Reticulum - Design

## Overview

Run a [Reticulum](https://reticulum.network/) presence on the homelab: a **transport node**
(`rnsd`) reachable from the internet and LAN over raw TCP, and an **LXMF propagation node**
(`lxmd`) that stores messages for peers that are offline and forwards them when the peer
reappears. Both run in the `reticulum` namespace as separate single-replica Deployments.

- `rnsd` owns an IFAC-protected `BackboneInterface` on port 4242 and acts as the entry point.
- `lxmd` is a Reticulum client of the same instance; it dials the `rnsd` ClusterIP for transport.
- Node identities and the IFAC passphrase live in SOPS-encrypted Secrets. No PVCs, no probes.

## Decisions

- **Raw TCP 4242 over a MetalLB LoadBalancer, not HTTP.** Reticulum is not HTTP; Traefik cannot
  carry it. The service uses the `external` MetalLB pool and is published as
  `1.rns.layertwo.dev`.
- **`externalTrafficPolicy: Local`.** The Backbone interface has a fast-flapping guard that bans
  a source IP after repeated short-lived connections. With `Cluster` policy every client would
  be SNATed to a single node IP and one flapping client could ban that IP for everyone; `Local`
  preserves real client IPs.
- **No liveness/readiness/startup probes.** A TCP probe is a connect-and-close, which looks like
  flapping and can trip the same ban. `rnsd` exits on interface error (`panic_on_interface_error
  = yes` in its config), so a kubelet restart covers liveness. There is deliberately no Gatus TCP
  check for the same reason.
- **One image, two commands.** `rnsd` and `lxmd` come from the same image
  (`ghcr.io/layertwo/reticulum`); `lxmd` overrides the entrypoint command. The image is built by
  `.github/workflows/reticulum-docker-image.yml` and pinned here by digest
  (`latest@sha256:...`) so a rebuild cannot silently change the deployed runtime.
- **Namespace/service naming.** The namespace is `reticulum` and the ClusterIP Service is
  force-renamed to the bare name `reticulum`, so `lxmd`'s configured remote
  `reticulum.reticulum.svc.cluster.local` resolves. app-template would otherwise name it
  `<release>-main`.
- **SOPS/age for all secrets.** The transport identity, the LXMF identity, the `rnsd` config
  (IFAC passphrase + BackboneInterface) and `lxmd`'s client `rns` config are encrypted with the
  repo age key. The propagation node's own config is a plain ConfigMap; only the identity is
  secret.
- **`emptyDir` only, no PVCs.** Everything `rnsd` writes is a regenerable cache. `lxmd`'s message
  store is `emptyDir` too: queued messages for offline devices are lost on a pod restart. Swap
  the `lxmd` volume for a PVC if that ever matters.
- **Hardened pods.** Non-root (`1000:1000`), read-only root filesystem, all capabilities dropped,
  `RuntimeDefault` seccomp, no service-account token. Secret files are mounted mode `0440`
  (root:1000, group-readable).

## Directory Structure

```
clusters/home/apps/cloud/reticulum/
├── namespace.yml
├── kustomization.yml
├── rnsd/
│   ├── kustomization.yml
│   ├── release.yml            # HelmRelease "reticulum": rnsd + ClusterIP + LoadBalancer
│   └── secrets-rnsd.sops.yml  # transport_identity, config (IFAC + BackboneInterface)
└── lxmd/
    ├── kustomization.yml
    ├── configmap.yml          # propagation + lxmf + logging config
    ├── release.yml            # HelmRelease "lxmd": propagation node
    └── secrets-lxmd.sops.yml  # identity, rns-config (client transport to rnsd)

containers/reticulum/          # shared rnsd/lxmd image (uv, rns, lxmf)
.github/workflows/reticulum-docker-image.yml
```

## rnsd (transport node)

- Image: `ghcr.io/layertwo/reticulum` (entrypoint `rnsd --config /config`).
- Config mounted from the `secrets-rnsd` Secret at `/config/config`; transport identity at
  `/config/storage/transport_identity`. A separate `emptyDir` is mounted at `/config/storage` so
  the directory is created with the pod's `fsGroup` and is writable before the identity file
  lands there.
- Exposes two Services: a ClusterIP (`reticulum`, used by `lxmd`) and a LoadBalancer
  (`reticulum-lb`, external traffic), both on TCP 4242.
- `reticulum-lb` annotations: `metallb.io/address-pool: external`,
  `external-dns.alpha.kubernetes.io/hostname: 1.rns.layertwo.dev`,
  `external-dns.alpha.kubernetes.io/cloudflare-proxied: "false"` (raw TCP; Cloudflare's proxy only
  carries HTTP), and `layertwo.dev/publish: all` (UniFi serves the LAN record, Cloudflare the
  public one).

## lxmd (propagation node)

- Same image, command `lxmd --config /lxmd --rnsconfig /rns`.
- Propagation is enabled in the ConfigMap (`[propagation] enable_node = yes`), not with a flag,
  so the config file remains the source of truth. `auth_required = no`: IFAC on the hub already
  decides who can reach the node.
- `[lxmf] display_name` and announce settings come from the ConfigMap; the LXMF identity and the
  client Reticulum config (`rns-config`) come from the `secrets-lxmd` Secret.
- Mounts: `/lxmd` (`emptyDir`, message store), `/lxmd/config` (ConfigMap), `/rns`
  (`emptyDir`, client cache), plus the identity and `rns-config` from the Secret.

## Verification / Follow-ups

- Manual: forward TCP 4242 on the UniFi router to the LoadBalancer IP once MetalLB assigns it,
  then pin that IP with `metallb.io/loadBalancerIPs` in `rnsd/release.yml` so a Service re-create
  cannot move the address the router forwards to.
- Confirm `1.rns.layertwo.dev` resolves to that LoadBalancer IP and is unproxied. With
  `--default-targets` scoped to the `crd` source, external-dns should publish an A record to the
  LB IP; the `cloudflare-proxied: "false"` annotation keeps it off the Cloudflare proxy.
- Nothing here has been run on the cluster yet.
