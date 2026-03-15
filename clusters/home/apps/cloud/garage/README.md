# Garage

Self-hosted S3-compatible object storage running on Kubernetes.

- S3 API: `https://*.s3.layertwo.dev` / `https://s3.layertwo.dev`
- S3 Website: `https://*.s3-website.layertwo.dev`
- Admin API: `https://garage-admin.layertwo.dev`

All commands exec into the pod. The `garage` binary is at `/garage`.

```sh
alias gexec='kubectl exec -n garage deploy/garage -- /garage'
```

## Cluster layout

### Initial setup (first deploy)

```sh
# Get the node ID from logs or:
gexec node id

# Assign the node to a zone with capacity matching the data PVC (1024G)
gexec layout assign -z dc1 -c 1024G <node-id>

# Review and apply
gexec layout show
gexec layout apply --version 1
```

### View current layout

```sh
gexec layout show
gexec status
```

## Buckets

### Create a bucket

```sh
gexec bucket create <bucket-name>
```

### List buckets

```sh
gexec bucket list
```

### Delete a bucket

```sh
gexec bucket delete <bucket-name>
```

### Enable website hosting on a bucket

```sh
gexec bucket website --allow <bucket-name>
```

The bucket will be accessible at `https://<bucket-name>.s3-website.layertwo.dev`.

## Access keys

### Create a key

```sh
gexec key create <key-name>
```

Outputs an `Access Key ID` and `Secret Access Key` — save these, the secret is not shown again.

### Grant a key access to a bucket

```sh
gexec bucket allow --read --write <bucket-name> --key <key-name>
# Add --owner to allow the key to manage bucket settings
```

### Revoke access

```sh
gexec bucket deny --read --write <bucket-name> --key <key-name>
```

### List keys

```sh
gexec key list
```

### Show key details (ID, permissions)

```sh
gexec key info <key-name>
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
