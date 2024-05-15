# cloudflare-ddns

This Python script allows you to update DNS records on CloudFlare dynamically. It retrieves the external IP address of the machine it's running on and updates the specified DNS record accordingly.

## Prerequisites

- Python 3.x
- Dependencies listed in `requirements.txt`
- Access to a CloudFlare account with appropriate permissions
- Environment variables set up for CloudFlare API token (`TOKEN`), zone ID (`ZONE_ID`), DNS name (`DNS_NAME`), and optionally for proxy status (`ENABLE_PROXY`)

## Configuration

`TOKEN`: Your CloudFlare API token.
`ZONE_ID`: The ID of the CloudFlare zone where the DNS record is located.
`DNS_NAME`: The name of the DNS record to update.
`ENABLE_PROXY` (optional): Set to true to enable CloudFlare proxying for the DNS record, false to disable.

## Usage
### Running as Docker Container

1. Pull the Docker image from Docker Hub:

```bash
docker pull ghcr.io/layertwo/cloudflare-ddns:latest
```

2. Run the Docker container with the required environment variables:

```bash
docker run -e TOKEN=your_cloudflare_token -e ZONE_ID=your_zone_id -e DNS_NAME=your_dns_name -e ENABLE_PROXY=true layertwo/cloudflare-ddns
```

Replace `your_cloudflare_token`, `your_zone_id`, and `your_dns_name` with your CloudFlare API token, zone ID, and DNS name respectively. Set `ENABLE_PROXY` to `true` to enable CloudFlare proxying for the DNS record.

### Running locally
Set up the required environment variables (`TOKEN`, `ZONE_ID`, `DNS_NAME`, `ENABLE_PROXY`).

Run the script:

```bash
python3 cloudflare_ddns.py
```
The script will retrieve the external IP address and update the CloudFlare DNS record accordingly.
