# OIDC to SAML Bridge

Bridge between OpenID Connect (OIDC) identity providers and SAML 2.0 service providers, designed to connect pocket-id to AWS IAM Identity Center.

## Why This Exists

AWS IAM Identity Center only supports SAML 2.0 for external identity providers, but pocket-id only supports OIDC. This bridge translates between the two protocols.

## Architecture

```
┌──────────────────────┐
│  AWS IAM Identity    │
│       Center         │
└──────────┬───────────┘
           │ SAML AuthnRequest
           ▼
┌──────────────────────┐         ┌──────────────────────┐
│   oidc-saml-bridge   │  OIDC   │     pocket-id        │
│  (aws-sso.layertwo   │────────▶│  (idp.layertwo.dev)  │
│        .dev)         │◀────────│                      │
└──────────┬───────────┘         └──────────────────────┘
           │ SAML Response
           ▼
┌──────────────────────┐
│  AWS IAM Identity    │
│       Center         │
└──────────────────────┘
```

## Flow

1. User accesses AWS via IAM Identity Center
2. IAM Identity Center sends a SAML AuthnRequest to the bridge `/saml/sso` endpoint (HTTP-Redirect or HTTP-POST binding)
3. Bridge redirects user to pocket-id for OIDC authentication
4. User authenticates with pocket-id
5. pocket-id redirects back to bridge `/callback` with an authorization code
6. Bridge exchanges the code for tokens, fetches user info, and builds a signed SAML assertion
7. Bridge POSTs the SAML response to the IAM Identity Center ACS URL
8. User is logged into AWS

## Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check (verifies OIDC provider connectivity) |
| `/saml/metadata` | GET | SAML IdP metadata XML (upload to IAM Identity Center) |
| `/saml/sso` | GET, POST | Receives SAML AuthnRequest from IAM Identity Center |
| `/callback` | GET | OIDC callback from pocket-id |

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `BRIDGE_URL` | Public base URL of the bridge (used to build the SSO URL in `/saml/metadata`) | Yes |
| `OIDC_ISSUER` | pocket-id issuer URL | Yes |
| `OIDC_CLIENT_ID` | OIDC client ID | Yes |
| `OIDC_CLIENT_SECRET` | OIDC client secret | Yes |
| `OIDC_REDIRECT_URI` | OAuth callback URL | Yes |
| `OIDC_SCOPES` | OIDC scopes | No (default: `openid profile email groups`) |
| `SAML_ENTITY_ID` | Bridge entity ID | Yes |
| `SAML_ACS_URL` | IAM Identity Center ACS URL | Yes |
| `SAML_AUDIENCE` | IAM Identity Center issuer URL | Yes |
| `CERT_PATH` | Path to SAML signing certificate (PEM) | No (default: `/certs/saml.crt`) |
| `KEY_PATH` | Path to SAML signing private key (PEM) | No (default: `/certs/saml.key`) |
| `SECRET_KEY` | Flask session signing secret | Yes |
| `SESSION_COOKIE_SECURE` | HTTPS-only cookies | No (default: `true`) |
| `SESSION_COOKIE_HTTPONLY` | HttpOnly cookies | No (default: `true`) |
| `SESSION_COOKIE_SAMESITE` | SameSite cookie policy | No (default: `Lax`) |
| `DEBUG` | Enable debug mode | No (default: `false`) |

### Where to find the AWS values

In the IAM Identity Center console, go to **Settings** > **Identity source** tab > **Change identity source** > **External identity provider**. Under **Service provider metadata** you will find:

- **IAM Identity Center Assertion Consumer Service (ACS) URL** — set this as `SAML_ACS_URL`
- **IAM Identity Center issuer URL** — set this as `SAML_AUDIENCE`

See the AWS documentation on connecting an external identity provider for the full walkthrough (link in References below).

## SAML Attributes

The bridge maps OIDC claims to the following SAML attributes:

| SAML Attribute | Source | Notes |
|---------------|--------|-------|
| `NameID` (format: `emailAddress`) | OIDC `email` claim | Required by IAM Identity Center, must match a username in Identity Center |
| `email` | OIDC `email` claim | |
| `name` | OIDC `name` claim | Falls back to email if not present |
| `RoleSessionName` | Local part of email (before `@`) | Full attribute name: `https://aws.amazon.com/SAML/Attributes/RoleSessionName` |
| `PrincipalTag:groups` | OIDC `groups` claim | Only included if groups are present, requires ABAC to be enabled in IAM Identity Center |

For `PrincipalTag:groups` to work, enable Attributes for access control in IAM Identity Center (link in References below).

## Prerequisites

### User Provisioning

IAM Identity Center does **not** support just-in-time user creation via SAML. Users must be pre-provisioned in IAM Identity Center before they can authenticate through this bridge. You can provision users manually or via SCIM. The NameID (email) in the SAML assertion must exactly match the username of an existing IAM Identity Center user.

### SAML Certificate

Generate an RSA 2048-bit self-signed certificate:

```bash
openssl genrsa -out saml.key 2048
openssl req -new -x509 -key saml.key -out saml.crt -days 365 \
  -sha256 -subj "/CN=aws-sso.layertwo.dev"
```

## Setup Steps

1. **Create OIDC client in pocket-id:**
   - Client ID: `aws-sso-bridge`
   - Redirect URI: `https://aws-sso.layertwo.dev/callback`
   - Scopes: `openid`, `profile`, `email`, `groups`

2. **Generate SAML certificate** (see above)

3. **Deploy the bridge** with the required environment variables and certificate volume mount

4. **Download metadata:**
   ```bash
   curl https://aws-sso.layertwo.dev/saml/metadata -o metadata.xml
   ```

5. **Configure IAM Identity Center:**
   - Go to IAM Identity Center console > **Settings** > **Identity source** > **Change identity source**
   - Select **External identity provider**
   - Copy the **ACS URL** and **Issuer URL** for your bridge config (`SAML_ACS_URL` and `SAML_AUDIENCE`)
   - Upload the `metadata.xml` from the bridge

6. **Provision users** in IAM Identity Center (manually or via SCIM) with usernames matching email addresses from pocket-id

## Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Run linting
black --check src tests
isort --check-only src tests
flake8 src tests

# Run tests (100% coverage required)
pytest
```

## Security

- SAML assertions are signed with RSA-SHA256 using exclusive XML canonicalization
- OIDC state and nonce parameters prevent CSRF and token replay
- XML parser configured to prevent XXE attacks
- Error responses are escaped to prevent reflected XSS
- Session cookies are Secure, HttpOnly, SameSite=Lax
- IAM Identity Center does not support encrypted SAML assertions

## Troubleshooting

- **"An unexpected error has occurred" on sign-in** — Verify the NameID (email) matches an existing IAM Identity Center username exactly.
- **SAML assertion audience mismatch** — Ensure `SAML_AUDIENCE` is set to the IAM Identity Center issuer URL, not the ACS URL.
- **Health check failing** — The bridge cannot reach the OIDC provider. Verify `OIDC_ISSUER` and network connectivity.
- **CloudTrail** — Filter on the `ExternalIdPDirectoryLogin` event name for detailed sign-in failure logs.

## References

- IAM Identity Center external IdP setup: https://docs.aws.amazon.com/singlesignon/latest/userguide/how-to-connect-idp.html
- SAML federation requirements: https://docs.aws.amazon.com/singlesignon/latest/userguide/other-idps.html
- Attributes for access control (ABAC): https://docs.aws.amazon.com/singlesignon/latest/userguide/attributesforaccesscontrol.html
- User provisioning (SCIM): https://docs.aws.amazon.com/singlesignon/latest/userguide/manage-your-identity-source-idp.html
- Troubleshooting: https://docs.aws.amazon.com/singlesignon/latest/userguide/troubleshooting.html
