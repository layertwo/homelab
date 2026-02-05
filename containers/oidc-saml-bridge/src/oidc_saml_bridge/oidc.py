"""OIDC client for authenticating with pocket-id."""

from typing import Any
from urllib.parse import urlencode

import requests


class OIDCClient:
    """OpenID Connect client for pocket-id."""

    def __init__(
        self,
        issuer: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: str = "openid profile email groups",
    ) -> None:
        self.issuer = issuer.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = scopes
        self._config: dict[str, Any] | None = None

    @property
    def config(self) -> dict[str, Any]:
        """Fetch and cache OIDC discovery configuration."""
        if self._config is None:
            self._config = self._fetch_config()
        return self._config

    def _fetch_config(self) -> dict[str, Any]:
        """Fetch OIDC discovery document."""
        url = f"{self.issuer}/.well-known/openid-configuration"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()

    def get_authorization_url(self, state: str, nonce: str) -> str:
        """Build the authorization URL for the OIDC provider."""
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self.scopes,
            "state": state,
            "nonce": nonce,
        }
        return f"{self.config['authorization_endpoint']}?{urlencode(params)}"

    def exchange_code(self, code: str) -> dict[str, Any]:
        """Exchange authorization code for tokens."""
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        response = requests.post(
            self.config["token_endpoint"],
            data=data,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def get_userinfo(self, access_token: str) -> dict[str, Any]:
        """Fetch user information from the OIDC provider."""
        response = requests.get(
            self.config["userinfo_endpoint"],
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
