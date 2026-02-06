import os
from functools import cached_property

from oidc_saml_bridge.oidc import OIDCClient
from oidc_saml_bridge.saml import SAMLBuilder


class ServiceProvider:

    @cached_property
    def oidc_issuer(self) -> str:
        return os.environ["OIDC_ISSUER"]

    @cached_property
    def oidc_client_id(self) -> str:
        return os.environ["OIDC_CLIENT_ID"]

    @cached_property
    def oidc_client_secret(self) -> str:
        return os.environ["OIDC_CLIENT_SECRET"]

    @cached_property
    def oidc_redirect_uri(self) -> str:
        return os.environ["OIDC_REDIRECT_URI"]

    @cached_property
    def oidc_scopes(self) -> str:
        return os.environ.get("OIDC_SCOPES", "openid profile email groups")

    @cached_property
    def saml_entity_id(self) -> str:
        return os.environ["SAML_ENTITY_ID"]

    @cached_property
    def saml_acs_url(self) -> str:
        return os.environ["SAML_ACS_URL"]

    @cached_property
    def saml_audience(self) -> str:
        return os.environ["SAML_AUDIENCE"]

    @cached_property
    def cert_path(self) -> str:
        return os.environ.get("CERT_PATH", "/certs/saml.crt")

    @cached_property
    def key_path(self) -> str:
        return os.environ.get("KEY_PATH", "/certs/saml.key")

    @cached_property
    def secret_key(self) -> str:
        return os.environ["SECRET_KEY"]

    @cached_property
    def debug(self) -> bool:  # pragma: no cover
        return os.environ.get("DEBUG", "false").lower() == "true"

    @cached_property
    def session_cookie_secure(self) -> bool:
        return os.environ.get("SESSION_COOKIE_SECURE", "true").lower() == "true"

    @cached_property
    def session_cookie_samesite(self) -> str:
        return os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")

    @cached_property
    def session_cookie_httponly(self) -> bool:
        return os.environ.get("SESSION_COOKIE_HTTPONLY", "true").lower() == "true"

    @cached_property
    def oidc_client(self) -> OIDCClient:
        return OIDCClient(
            issuer=self.oidc_issuer,
            client_id=self.oidc_client_id,
            client_secret=self.oidc_client_secret,
            redirect_uri=self.oidc_redirect_uri,
            scopes=self.oidc_scopes,
        )

    @cached_property
    def saml_builder(self) -> SAMLBuilder:
        return SAMLBuilder(
            entity_id=self.saml_entity_id,
            acs_url=self.saml_acs_url,
            cert_path=self.cert_path,
            key_path=self.key_path,
        )
