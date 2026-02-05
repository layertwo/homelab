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
2. IAM Identity Center redirects to bridge `/saml/sso` endpoint
3. Bridge redirects user to pocket-id for OIDC authentication
4. User authenticates with pocket-id
5. pocket-id redirects back to bridge `/callback`
6. Bridge creates signed SAML assertion
7. Bridge POSTs SAML assertion to IAM Identity Center
8. User is logged into AWS

## Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Health check |
| `GET /saml/metadata` | SAML IdP metadata (upload to AWS) |
| `GET /saml/sso` | Receives SAML AuthnRequest from AWS |
| `GET /callback` | OIDC callback from pocket-id |

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OIDC_ISSUER` | pocket-id issuer URL | Yes |
| `OIDC_CLIENT_ID` | OIDC client ID | Yes |
| `OIDC_CLIENT_SECRET` | OIDC client secret | Yes |
| `OIDC_REDIRECT_URI` | OAuth callback URL | Yes |
| `OIDC_SCOPES` | OIDC scopes | No (default: openid profile email groups) |
| `SAML_ENTITY_ID` | Bridge entity ID | Yes |
| `SAML_ACS_URL` | IAM Identity Center ACS URL | Yes |
| `SAML_AUDIENCE` | SAML audience | No (defaults to ACS URL) |
| `CERT_PATH` | Path to SAML signing cert | No (default: /certs/saml.crt) |
| `KEY_PATH` | Path to SAML signing key | No (default: /certs/saml.key) |
| `SECRET_KEY` | Flask session secret | Yes |
| `DEBUG` | Enable debug mode | No (default: false) |

## SAML Certificate

Generate a 1-year RSA 2048-bit certificate:

```bash
openssl genrsa -out saml.key 2048
openssl req -new -x509 -key saml.key -out saml.crt -days 365 \
  -sha256 -subj "/CN=aws-sso.layertwo.dev"
```

## Setup Steps

1. Create OIDC client in pocket-id:
   - Client ID: `aws-sso-bridge`
   - Redirect URI: `https://aws-sso.layertwo.dev/callback`
   - Scopes: `openid`, `profile`, `email`, `groups`

2. Generate SAML certificate (see above)

3. Deploy the bridge

4. Get metadata: `curl https://aws-sso.layertwo.dev/saml/metadata`

5. In AWS IAM Identity Center:
   - Settings → Identity source → Change identity source
   - Select "External identity provider"
   - Upload the metadata XML

## Development

```bash
# Install dependencies
pip install -e .[dev]

# Run linting
black --check src tests
isort --check-only src tests
flake8 src tests

# Run tests
pytest
```

## Security

- SAML assertions are signed with RSA-SHA256
- Cookie sessions are signed with itsdangerous
- Session cookies are HttpOnly and Secure (in production)
- 1-year certificate validity for regular rotation
