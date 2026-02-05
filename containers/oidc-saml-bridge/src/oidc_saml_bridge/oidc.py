"""OIDC client for authenticating with pocket-id."""

from functools import cached_property
from typing import Any
from urllib.parse import urlencode

import jwt
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
        self._session = requests.Session()

    @cached_property
    def config(self) -> dict[str, Any]:
        """Fetch OIDC discovery document."""
        url = f"{self.issuer}/.well-known/openid-configuration"
        response = self._session.get(url, timeout=10)
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

    def exchange_code(self, code: str, expected_nonce: str | None = None) -> dict[str, Any]:
        """Exchange authorization code for tokens and validate nonce."""
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        response = self._session.post(
            self.config["token_endpoint"],
            data=data,
            timeout=10,
        )
        response.raise_for_status()
        tokens = response.json()

        # Validate ID token nonce if provided
        if expected_nonce and "id_token" in tokens:
            self._validate_id_token(tokens["id_token"], expected_nonce)

        return tokens

    def _validate_id_token(self, id_token: str, expected_nonce: str) -> None:
        """Validate ID token nonce without full signature verification."""
        # Decode without verification to check nonce (signature verification requires jwks)
        try:
            payload = jwt.decode(
                id_token,
                options={"verify_signature": False},
                algorithms=["RS256", "HS256"],
            )
            token_nonce = payload.get("nonce")
            if token_nonce != expected_nonce:
                raise ValueError("ID token nonce mismatch")
        except jwt.PyJWTError as e:
            raise ValueError(f"Invalid ID token: {e}")

    def get_userinfo(self, access_token: str) -> dict[str, Any]:
        """Fetch user information from the OIDC provider."""
        response = self._session.get(
            self.config["userinfo_endpoint"],
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
