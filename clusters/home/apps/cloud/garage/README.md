# Garage

Self-hosted S3-compatible object storage. Runs as a TrueNAS app (not in Kubernetes) —
this directory only holds the IngressRoutes/cert/Service pointer that route
`s3.layertwo.dev` traffic to it.

- S3 API: `https://*.s3.layertwo.dev` / `https://s3.layertwo.dev`
- S3 Website: `https://*.s3-website.layertwo.dev`

Admin commands (`garage bucket/key/...`) run from a shell on the TrueNAS app
itself, not via `kubectl exec` — there's no in-cluster pod anymore. Open a
shell on the app in the TrueNAS UI and run `garage` directly (no alias
needed, it's already on the container's `PATH`).

## Cluster layout

### Initial setup (first deploy)

```sh
# Get the node ID from logs or:
garage node id

# Assign the node to a zone with capacity matching the storage allocated to the app
garage layout assign -z dc1 -c <capacity> <node-id>

# Review and apply
garage layout show
garage layout apply --version 1
```

### View current layout

```sh
garage layout show
garage status
```

## Buckets

### Create a bucket

```sh
garage bucket create <bucket-name>
```

### List buckets

```sh
garage bucket list
```

### Delete a bucket

```sh
garage bucket delete <bucket-name>
```

### Enable website hosting on a bucket

```sh
garage bucket website --allow <bucket-name>
```

The bucket will be accessible at `https://<bucket-name>.s3-website.layertwo.dev`.

## Access keys

### Create a key

```sh
garage key create <key-name>
```

Outputs an `Access Key ID` and `Secret Access Key` — save these, the secret is not shown again.

### Grant a key access to a bucket

```sh
garage bucket allow --read --write <bucket-name> --key <key-name>
# Add --owner to allow the key to manage bucket settings
```

### Revoke access

```sh
garage bucket deny --read --write <bucket-name> --key <key-name>
```

### List keys

```sh
garage key list
```

### Show key details (ID, permissions)

```sh
garage key info <key-name>
```

## Using with AWS CLI

```sh
aws configure --profile garage
# AWS Access Key ID: <key-id>
# AWS Secret Access Key: <secret>
# Default region: garage
# Default output format: json

aws --profile garage --endpoint-url https://s3.layertwo.dev s3 ls
aws --profile garage --endpoint-url https://s3.layertwo.dev s3 cp file.txt s3://<bucket-name>/
```
