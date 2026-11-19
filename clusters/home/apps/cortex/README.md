# Cortex

Zero-knowledge photo/video backup. The browser encrypts files, metadata and tags before
they leave the device; the API only stores ciphertext.

- **API + web**: one `app-template` HelmRelease (`release.yml`), services `cortex-api` and `cortex-web`
- **Metadata**: ScyllaDB Alternator (`cortex-db`), 3 members on the node-local `local-path` storage class
- **Blobs**: Garage bucket `cortex-files` at `https://s3.layertwo.dev`
- **Auth**: Pocket ID (generic OIDC, authorization code + PKCE); the SPA reads `/v1/config` at startup
- **Ingress**: `https://cortex.layertwo.dev`; `/v1` → API, everything else → the static SPA

## First-time setup

The manifests ship with placeholders; the API will not become Ready until the two stores
are configured.

### 1. Pocket ID client

Create a **public** OIDC client (PKCE, no secret):

- Redirect URI: `https://cortex.layertwo.dev/auth/callback`
- Scopes: `openid profile email offline_access`

Put the client id in `configmap.yml` (`OIDC_CLIENT_ID`).

### 2. Garage bucket and key

On the TrueNAS app shell:

```sh
garage bucket create cortex-files
garage key create cortex-api
garage bucket allow --read --write --owner cortex-files --key cortex-api
```

Allow the browser to upload directly (the API signs URLs for this origin):

```sh
aws --profile garage --endpoint-url https://s3.layertwo.dev s3api put-bucket-cors \
  --bucket cortex-files \
  --cors-configuration '{"CORSRules":[{"AllowedOrigins":["https://cortex.layertwo.dev"],"AllowedMethods":["GET","PUT","HEAD"],"AllowedHeaders":["*"],"ExposeHeaders":["ETag"],"MaxAgeSeconds":3000}]}'
```

Put the key id/secret into the SOPS secret:

`sops clusters/home/apps/cortex/secrets-cortex.sops.yml`

(replace `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY`).

### 3. ScyllaDB Alternator credentials

Alternator uses the CQL role's `salted_hash` as the AWS secret key and the role name as
the access key. Once `cortex-db` is Ready:

```sh
kubectl -n cortex exec -it service/cortex-db-client -c scylla -- \
  cqlsh --user cassandra --no-color \
  -e "SELECT salted_hash FROM system.roles WHERE role='cassandra';"
```

Put it into the SOPS secret as `DYNAMODB_SECRET_ACCESS_KEY` (`DYNAMODB_ACCESS_KEY_ID`
is already `cassandra`), then push.

### 4. Re-run the bootstrap and API

The bootstrap Job creates `cortex-data` (PK/SK + GSI1/GSI2) and `cortex-shares` (PK/SK +
TTL). It retries while Alternator starts; after fixing the secret, delete it so Flux
recreates it with the new credentials:

```sh
kubectl -n cortex delete job cortex-bootstrap
kubectl -n cortex rollout restart deploy/cortex-api
```

Then open `https://cortex.layertwo.dev` and create a vault.

## Notes

- **Alternator is HTTP inside the cluster** (`insecureEnableHTTP: true`), with
  authentication still enabled. TLS would need a per-service CA bundle because the API
  also talks to Garage over HTTPS.
- **`local-path` is node-local.** A node loss loses that replica; RF=3 tolerates one node.
  Scylla may also want a `NodeConfig` for AIO limits on these nodes.
- **No backups are wired yet.** Encrypted blobs live in Garage and metadata in Scylla;
  losing Scylla loses the vault/item structure even though the blobs survive. Add Scylla
  snapshots + a Garage bucket backup before uploading irreplaceable data.
- `s3.layertwo.dev` already resolves internally through the existing DNS, so the API
  uses the public hostname and presigned URLs stay reachable by the browser.
- `cortex-api` / `cortex-web` use `:latest` with `imagePullPolicy: Always`; pin digests
  once the images settle.
- `readinessProbe` is `/v1/health` (DynamoDB + S3); it stays 503 until the credentials
  are valid. `livenessProbe` is `/v1/config`, which needs no dependency.
- `AWS_REGION` is `garage` because Garage validates the SigV4 region against its
  `s3_region`. Alternator accepts the same value (it signs with whatever region the
  client sends).
