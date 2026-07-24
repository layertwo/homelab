# Homelab Networking

This document provides detailed information about the networking setup in the homelab.

## Overview

The homelab uses a multi-tier networking approach with separate internal and external networks. This allows for secure access to services while maintaining isolation where needed.

## Network Components

### MetalLB

MetalLB provides load balancing for Kubernetes services, allowing them to be exposed with dedicated IP addresses. The homelab uses two IP pools:

- **Internal Pool**: 172.31.0.20-172.31.0.29
  - Used for services that should only be accessible within the local network
  - Configured with L2 advertisement

- **External Pool**: 172.31.0.30-172.31.0.39
  - Used for services that should be accessible from outside the local network
  - Configured with L2 advertisement

### Traefik

Traefik serves as the ingress controller with two separate instances:

#### Internal Traefik (172.31.0.20)

- Handles internal traffic
- Configured with the `internal` ingress class
- Accessible at `proxy-internal.layertwo.dev`
- Dashboard available at `traefik-internal.layertwo.dev`

#### External Traefik (172.31.0.30)

- Handles external traffic
- Configured with the `external` ingress class
- Uses TLS with a wildcard certificate for `*.layertwo.dev`
- Dashboard available at `traefik-external.layertwo.dev`
- Configured with strict TLS settings:
  - TLS 1.2/1.3 only
  - Strong cipher suites
  - SNI strict mode

### External DNS

External DNS runs as two separate instances that manage DNS records based on Kubernetes services and ingresses:

- **external-dns-cloudflare**: uses the `cloudflare` provider to write records in Cloudflare for the `layertwo.dev` domain
- **external-dns-unifi**: uses a webhook provider to write records directly to the UniFi gateway for the `layertwo.dev` and `layertwo.lan` domains

Both instances watch for the `external-dns.alpha.kubernetes.io/hostname` annotation to determine the record name, but which instance actually creates the record is controlled by the `layertwo.dev/publish` annotation:

- `layertwo.dev/publish: "external"` (or `"all"`) — picked up by `external-dns-cloudflare`
- `layertwo.dev/publish: "internal"` (or `"all"`) — picked up by `external-dns-unifi`

Both instances:

- Update existing DNS records when IP addresses change
- Remove DNS records when services are deleted

### Cloudflare DDNS

The custom Cloudflare DDNS container updates DNS records on Cloudflare with the current external IP address. This ensures that the homelab is accessible even when the external IP address changes.

## Network Flow

1. External requests come in through the router and are forwarded to the External Traefik instance (172.31.0.30)
2. External Traefik routes the requests to the appropriate services based on the hostname
3. Internal requests are routed through the Internal Traefik instance (172.31.0.20)
4. Both Traefik instances use MetalLB for load balancing

## Security Considerations

- External Traefik is configured with strict TLS settings to ensure secure connections
- Internal services are only accessible through the Internal Traefik instance
- Pocket ID (`clusters/home/apps/security/pocket-id/`, namespace `pocket-id`) provides OIDC authentication for services that require it, available at `idp.layertwo.dev`
- An OIDC-to-SAML bridge in front of Pocket ID provides SAML SSO for AWS at `aws-sso.layertwo.dev`
- Network policies can be used to further restrict traffic between services

## Troubleshooting

### DNS Issues

If DNS resolution is not working:

1. Check the CoreDNS custom zone (`clusters/home/apps/kube-system/coredns/coredns-custom.yml`), which resolves `layertwo.dev` internally by forwarding queries to the UniFi gateway (172.31.0.1)
2. Check that External DNS is running properly
3. Verify that the service has the correct annotations
4. Check the Cloudflare DNS records

### Connectivity Issues

If services are not accessible:

1. Check that MetalLB is running properly
2. Verify that the service is using the correct MetalLB pool
3. Check that Traefik is routing traffic correctly
4. Verify that the service is running and healthy
