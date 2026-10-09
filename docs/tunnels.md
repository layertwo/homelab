# Tunnels

Self-hosted, ngrok-style tunnels. A creator runs [frp](https://github.com/fatedier/frp)'s `frpc` next to a local web app and gets `https://<handle>.w.tunnels.layertwo.dev`, behind a Pocket ID login. This page covers **Phase 0** (stock frp, no custom code); the design and later phases are in the [design doc](plans/2026-10-07-tunnels-design.md).

## How it works

| Piece | Where |
|---|---|
| Control channel | `wss://tunnels.layertwo.dev/~!frp` (Cloudflare-proxied) through the external Traefik to `frps` port 7000 |
| Sites | `https://<handle>.w.tunnels.layertwo.dev` (DNS-only wildcard, own certificate) through Traefik and the login gate to `frps` port 8080, which forwards to the creator's `frpc` |
| Creators | `frpc` logs in to `frps` with a Pocket ID access token (client credentials); `frps` checks the issuer and the audience `https://tunnels.layertwo.dev` itself |
| Visitors | pass the `tunnels-oidc` middleware ([traefik-oidc-auth](https://github.com/sevensolutions/traefik-oidc-auth), Pocket ID client `tunnels-gate`); only members of the Pocket ID groups `tunnels-viewers` or `tunnels-creators` get through |

Manifests: `clusters/home/apps/network/tunnels/`.

## Adding a tester (creator)

1. In Pocket ID create an OIDC client `tunnels-m2m-<name>`: confidential, API access to `Tunnels` as **Client access (M2M)**. Machine clients are not subject to group checks, so in Phase 0 holding a client is what makes someone a creator.
2. Give them the client id and secret out of band. They keep them in their environment as `TUNNELS_CLIENT_ID` and `TUNNELS_CLIENT_SECRET`, never in git.
3. Check the client: this prints `['https://tunnels.layertwo.dev']`.

   ```bash
   curl -s -d grant_type=client_credentials -d client_id="$TUNNELS_CLIENT_ID" -d client_secret="$TUNNELS_CLIENT_SECRET" \
     -d resource=https://tunnels.layertwo.dev https://idp.layertwo.dev/api/oidc/token | jq -r .access_token \
     | python3 -c "import sys,json,base64;t=sys.stdin.read().split('.')[1];print(json.loads(base64.urlsafe_b64decode(t+'='*(-len(t)%4)))['aud'])"
   ```

## Running a tunnel

Save this as `frpc.toml`. It is the file that was tested; change `user` and `subdomain` to your handle and `localIP` / `localPort` to your app (from the container, a service on your machine is `host.containers.internal`).

```toml
serverAddr = "tunnels.layertwo.dev"
serverPort = 443
user = "alice"
transport.protocol = "wss"
transport.heartbeatInterval = 30
transport.tls.trustedCaFile = "/etc/ssl/certs/ca-certificates.crt"
auth.method = "oidc"
auth.additionalScopes = ["HeartBeats"]
auth.oidc.clientID = "{{ .Envs.TUNNELS_CLIENT_ID }}"
auth.oidc.clientSecret = "{{ .Envs.TUNNELS_CLIENT_SECRET }}"
auth.oidc.tokenEndpointURL = "https://idp.layertwo.dev/api/oidc/token"
auth.oidc.additionalEndpointParams.resource = "https://tunnels.layertwo.dev"

[[proxies]]
name = "default"
type = "http"
localIP = "echo"
localPort = 80
subdomain = "alice"
```

Run it with the pinned container, or with a native `frpc` of the same version (v0.71.0):

```bash
podman run --rm -v "$PWD:/cfg:ro" -e TUNNELS_CLIENT_ID -e TUNNELS_CLIENT_SECRET \
  ghcr.io/fatedier/frpc:v0.71.0@sha256:99ece6a2b62cfc68731e0df289af804ff1c699911cfc47871856434f1d6d53ee -c /cfg/frpc.toml
```

`login to server success` and `start proxy success` mean the tunnel is up; opening `https://<subdomain>.w.tunnels.layertwo.dev` then asks for a Pocket ID login.

### Verify the server certificate

`frpc` does not verify the server certificate unless `transport.tls.trustedCaFile` is set: without it the client connects and hands its token to whatever answers. Always set it. The bundle path is `/etc/ssl/cert.pem` for a native client on macOS, `/etc/ssl/certs/ca-certificates.crt` on Debian and Ubuntu and inside the `frpc` container. A bundle that lacks the server's CA fails with `x509: certificate signed by unknown authority`.

## Adding a viewer

Add the Pocket ID user to `tunnels-viewers` (or `tunnels-creators`). Anyone else is refused by Pocket ID. The gate matches the group **Name**, which is what Pocket ID puts in the `groups` claim, not the Friendly name. The group form fills Name from the Friendly name and replaces every character outside `a-z0-9_` with `_`, so typing `tunnels-viewers` as the Friendly name gives the Name `tunnel_viewers`. Edit the Name to `tunnels-viewers` and `tunnels-creators`. The gate checks the groups again whenever the session token renews, which is about once an hour.

## What a site receives

- The request comes from Traefik with `Host: <handle>.w.tunnels.layertwo.dev`.
- Phase 0 adds `X-Tunnels-Sub`, `X-Tunnels-User` and `X-Tunnels-Groups` (one value per group). A client cannot set them; the gate overwrites them. Later phases replace them with a single `X-Tunnel-User`.
- The gate's own cookies (`__Secure-tunnels.*`) are removed; the app's cookies pass through. WebSockets work.

## Limits in Phase 0

- Names are first come, first served and trust-based: anyone holding a machine client can claim any free `subdomain` (one DNS label: lowercase letters, digits, hyphens). `user` only prefixes the proxy name.
- One global gate: every viewer can open every tunnel. There is no per-tunnel access or sharing yet.
- Only `http` proxies on a `subdomain` are usable. TCP proxies cannot bind (`allowPorts` allows only port 7000, which `frps` itself holds) and `https` / `tcpmux` are disabled; `udp` and `stcp` register but nothing outside can reach them.
- Revocation takes effect when tokens expire or renew, up to about an hour: remove the machine client, or remove the user from the groups.
- The gate owns `/oidc/callback` and any path starting with `/logout` on every site, so an app's own `/logout` never reaches it.

## Troubleshooting

| Symptom | Cause |
|---|---|
| `invalid OIDC token in login: oidc: expected audience "https://tunnels.layertwo.dev"` | the token request has no `resource`; keep `auth.oidc.additionalEndpointParams.resource` |
| `invalid_client` from the token endpoint | wrong client id or secret |
| `x509: certificate signed by unknown authority` | `trustedCaFile` points at a bundle without the server's CA |
| after login, frps shows "The page you requested was not found." | no tunnel is connected under that `subdomain` |
| after a successful login the gate shows "403 Forbidden: it seems like your account is not allowed to access this resource" | the ID token's `groups` claim contains neither `tunnels-viewers` nor `tunnels-creators`: compare the group names in Pocket ID (the **Name** field, see above) with the ones in the Traefik log line `Unauthorized. Expected claim groups to contain any value of [tunnels-viewers, tunnels-creators]`; if you rename a group, or add the user after logging in, log in again in a fresh private window |
| a script gets 401, a browser gets a login redirect | by design: only requests that accept `text/html` are redirected |
