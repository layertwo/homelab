# Nextcloud

Nextcloud (`nextcloud/helm` chart), exposed at `cloud.layertwo.dev` on the **external** Traefik.

- **Files** live in Garage (`garage-truenas.garage.svc.cluster.local:30188`, bucket `nextcloud`) as S3 *primary* storage — not on a PVC.
- **Identity** is Pocket ID via the `user_oidc` app, so logins still create real Nextcloud users. The local
  admin account is the break-glass path.
- **State** is CNPG `cnpg-nextcloud` (2 instances) + a standalone Valkey (cache + file locking).

## Before the first sync

Nothing below is automated; do these first.

**1. Garage bucket and key** (on the TrueNAS Garage shell — Garage is no longer in-cluster):

```sh
garage bucket create nextcloud
garage key create nextcloud-app
garage bucket allow --read --write --owner nextcloud --key nextcloud-app
```

The bucket must exist before the first boot. Nextcloud checks `HeadBucket` on every connection and, if it is
missing, calls `CreateBucket` itself — which fails the whole instance with `StorageNotAvailableException` unless
the key has bucket-create rights. (`autoCreate: false` in `release.yml` is a red herring: Nextcloud's
`S3ConnectionTrait` never reads that flag, only `verify_bucket_exists`, which is not settable from the chart.)

**2. Pocket ID OIDC client.** Register the client with both callback URLs — `user_oidc` redirects to the
`index.php` form unless pretty URLs are on, and Pocket ID matches redirect URIs by exact string:

```
https://cloud.layertwo.dev/index.php/apps/user_oidc/code
https://cloud.layertwo.dev/apps/user_oidc/code
```

**3. Fill in the secrets and encrypt them:**

- `app/secrets-nextcloud-admin.sops.yml` — local admin password
- `app/secrets-nextcloud-oidc.sops.yml` — client ID + secret from step 2
- `app/secrets-nextcloud-s3.sops.yml` — access key + secret from step 1
- `valkey/secrets-nextcloud-valkey.sops.yml` — any password (key name must stay `password`)

```sh
sops --encrypt --in-place clusters/home/apps/cloud/nextcloud/{app,valkey}/secrets-*.sops.yml
```

**4. Games directory.** Create `/mnt/storage0/media/games` on TrueNAS. The hook exposes
`movies`, `tv` and `games` over NFS as External Storage and skips `games` until the
directory exists.

## Layout

```
app/       HelmRelease, IngressRoute, secrets
postgres/  CNPG Cluster
valkey/    Valkey (official chart, standalone)
```

## External storage (media sharing)

The TrueNAS media export `/mnt/storage0/media` is mounted **read-only** into the pod
(`nextcloud.extraVolumes`/`extraVolumeMounts` at `/media`) and surfaced as three system-wide
**External Storage** mounts — `Movies`, `TV`, `Games` — so the library can be link-shared
without copying it into Garage.

- **Read-only is the whole point.** The mount is `readOnly: true`, so Nextcloud cannot
  rename/move/delete and cannot desync the Sonarr/Radarr/Jellyfin libraries that mount the
  same export directly.
- The mounts are registered from the `before-starting` hook with
  `occ files_external:create <name> local null::null -c datadir=...`, guarded by a
  `files_external:list` check so re-runs are free. Note Nextcloud's JSON escapes `/` as
  `\/`, which is why the guard greps the literal `\/`.
- No TrueNAS change is needed to *mount* it: every node IP is already in the export's host
  ACL (see [storage.md](../../../../docs/storage.md)).
- Files must be readable by uid 33 (`www-data`). If a browse comes up empty, check
  permissions on the NAS (`ls -ln` on a movie) before suspecting the mount.

## Design notes worth not re-litigating

**`trustedDomains` is read exactly once, at install.** The entrypoint pushes `NEXTCLOUD_TRUSTED_DOMAINS` into
`config.php` only while `installed_version == 0.0.0.0`; editing it afterwards does nothing, and the chart's
`NEXTCLOUD_UPDATE` path never rewrites it. Get it right before the first sync or run
`occ config:system:set trusted_domains ...` by hand.

`nextcloud.host` is load-bearing beyond the ingress host: the chart sends it as the `Host` header on the
liveness/readiness probes (`/status.php`), so a host that is not in `trustedDomains` means the pod never goes Ready.

**S3 checksums are safe with Garage.** Garage's composite-CRC32 bug (#1228) is a *response-side* defect that only
bites clients which opt into checksum validation. Nextcloud 34 pins both `request_checksum_calculation` and
`response_checksum_validation` to `when_required` (`S3ConnectionTrait`, stable34 = 34.0.4) and never sets
`ChecksumMode`, so no `x-amz-checksum-*` header is sent and no response checksum is verified. Garage also ignores
`x-amz-acl: private` and `x-amz-storage-class: STANDARD`, both of which Nextcloud sends unconditionally.
Uploads ≥ 100 MiB go multipart with 500 MiB parts; reads use raw range GETs.

**`OBJECTSTORE_S3_SSE_C_KEY` renders as `""` and is inert** — `if (getenv(...))` is falsey for an empty string, so
`sse_c_key` is never set.

**Valkey, standalone and ephemeral.** Nextcloud needs a cache and a file-lock store, nothing durable — so
`replica.enabled` stays false (the chart renders a Deployment, not a StatefulSet, in that mode) and
`dataStorage.enabled` stays false, giving an `emptyDir`. No PVC means nothing to back up and a restart clears any
stale file locks. Note the chart's `architecture: standalone` key that forgejo sets does **not exist** in this
chart — it's a silent no-op there; the real switch is `replica.enabled`.

The credentials are *not* generated. The chart's `templates/secret.yaml` has no `randAlphaNum`/`lookup`; it only
b64-encodes inline `auth.aclUsers.<user>.password` values or defers to `auth.usersExistingSecret`, which is what we
do. The passwordKey you name here is read verbatim by the init container:
`get_user_password "default" "<passwordKey>"` cats `/valkey-users-secret/<passwordKey>`, so renaming the key in the
Secret without renaming it here gives a hard init failure.

Nextcloud's chart calls the whole thing `externalRedis` regardless of server — that's its fixed key name mapping to
`REDIS_HOST`/`REDIS_HOST_PORT`/`REDIS_HOST_PASSWORD`. Valkey is Redis-protocol-compatible and the Nextcloud image
needs no changes; the `redis.config.php` shipped in the image is used as-is.

**No `nextcloud.configs` block on purpose.** The chart only mounts its own `defaultConfigs` when `nextcloud.configs`
is non-empty; with it empty, the official image's own `config/*.php` (byte-identical `s3.config.php`,
`reverse-proxy.config.php`, `redis.config.php`, `apcu.config.php`) are copied into `/var/www/html/config` on first
boot. Same result, less YAML. The config dir, `custom_apps` (where `occ app:install user_oidc` lands) and `data`
are all subPaths of the `nextcloud-nextcloud` PVC, so they survive restarts.

**`occ app:install user_oidc` runs from a `before-starting` hook, not `post-installation`.** `post-installation`
runs once, and a transient app-store failure there is silent and unrecoverable — the entrypoint has already written
`version.php`, so a retried pod skips the install branch and starts normally without the app. `before-starting`
runs on every start with a guard, so it self-heals. It never blocks boot: no `set -e`, and each step falls through
to an error line in the pod log. `occ user_oidc:provider` is an upsert, so re-running is free.

**`--unique-uid=0`** makes the Nextcloud user ID the Pocket ID `sub` verbatim. The default (`1`) hashes
`<providerRowId>_0_<sub>`, so deleting and recreating the provider would change every user ID and orphan their
files. Safe here because there is exactly one provider.

**Upgrade remediation is `RetryOnFailure`, not `rollback`.** Nextcloud migrates its schema on boot, which is
forward-only — `rollback` would loop forever on a failed upgrade.

## Deliberately not configured

- **SMTP / mail.** Add under `nextcloud.mail` plus `smtpHostKey`/`smtpUsernameKey`/`smtpPasswordKey` in
  `nextcloud.existingSecret`.
- **Metrics.** `metrics.enabled: true` + `serviceMonitor.enabled: true`; needs a token created in Nextcloud first.
- **Group provisioning / end-session logout.** Add `--group-provisioning=1 --mapping-groups=groups` and
  `--endsessionendpointuri` to the hook if Pocket ID ever emits groups.
- **Egress restriction.** The hook sets `allow_local_remote_servers=true` because `idp.layertwo.dev`
  resolves to the private Traefik/MetalLB IP, which Nextcloud's HTTP client blocks by default. That
  necessarily lets Nextcloud's server-side HTTP client reach private addresses. A scoped egress
  `NetworkPolicy` is the usual mitigation, but this cluster runs the default K3S flannel CNI with no
  policy engine, so NetworkPolicies are not enforced here — adding one would be inert. Revisit if a
  policy-enforcing CNI is adopted.
- **CNPG backups.** `cnpg-nextcloud` has no `spec.backup`; see "The gap to close first" below.

## The gap to close first

`cnpg-nextcloud` has **no `spec.backup`**, and neither does anything else except Immich. With S3 primary storage
the database *is* the index to every file in Garage — losing it orphans the whole bucket. Adding a
`barmanObjectStore` (copy `immich/postgres/secrets-cloudnativepg-r2.sops.yml` into this namespace, then mirror
`cnpg-immich.yml`'s `spec.backup` and add a `ScheduledBackup`) is the single highest-value follow-up. Do it before
putting real data in, not after: a no-op archiver is harmless, but deploying `spec.backup` with bad credentials
does fill the WAL volume.
