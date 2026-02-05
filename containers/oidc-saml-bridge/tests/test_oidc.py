"""Tests for the OIDC module."""

import pytest
import responses

from src.oidc_saml_bridge.oidc import OIDCClient


class TestOIDCClient:
    """Tests for OIDCClient class."""

    @pytest.fixture
    def oidc_config(self):
        """OIDC discovery configuration fixture."""
        return {
            "issuer": "https://idp.example.com",
            "authorization_endpoint": "https://idp.example.com/authorize",
            "token_endpoint": "https://idp.example.com/token",
            "userinfo_endpoint": "https://idp.example.com/userinfo",
        }

    @responses.activate
    def test_fetch_config(self, oidc_config):
        """Test fetching OIDC discovery configuration."""
        responses.add(
            responses.GET,
            "https://idp.example.com/.well-known/openid-configuration",
            json=oidc_config,
            status=200,
        )

        client = OIDCClient(
            issuer="https://idp.example.com",
            client_id="test-client",
            client_secret="test-secret",
            redirect_uri="https://bridge.example.com/callback",
        )

        config = client.config
        assert config["authorization_endpoint"] == "https://idp.example.com/authorize"

    @responses.activate
    def test_config_cached(self, oidc_config):
        """Test that config is cached."""
        responses.add(
            responses.GET,
            "https://idp.example.com/.well-known/openid-configuration",
            json=oidc_config,
            status=200,
        )

        client = OIDCClient(
            issuer="https://idp.example.com",
            client_id="test-client",
            client_secret="test-secret",
            redirect_uri="https://bridge.example.com/callback",
        )

        config1 = client.config
        config2 = client.config

        assert config1 is config2
        assert len(responses.calls) == 1

    @responses.activate
    def test_get_authorization_url(self, oidc_config):
        """Test building authorization URL."""
        responses.add(
            responses.GET,
            "https://idp.example.com/.well-known/openid-configuration",
            json=oidc_config,
            status=200,
        )

        client = OIDCClient(
            issuer="https://idp.example.com",
            client_id="test-client",
            client_secret="test-secret",
            redirect_uri="https://bridge.example.com/callback",
        )

        url = client.get_authorization_url(state="test-state", nonce="test-nonce")

        assert url.startswith("https://idp.example.com/authorize?")
        assert "response_type=code" in url
        assert "client_id=test-client" in url
        assert "redirect_uri=https%3A%2F%2Fbridge.example.com%2Fcallback" in url
        assert "state=test-state" in url
        assert "nonce=test-nonce" in url
        assert "scope=openid+profile+email+groups" in url

    @responses.activate
    def test_get_authorization_url_custom_scopes(self, oidc_config):
        """Test authorization URL with custom scopes."""
        responses.add(
            responses.GET,
            "https://idp.example.com/.well-known/openid-configuration",
            json=oidc_config,
            status=200,
        )

        client = OIDCClient(
            issuer="https://idp.example.com",
            client_id="test-client",
            client_secret="test-secret",
            redirect_uri="https://bridge.example.com/callback",
            scopes="openid email",
        )

        url = client.get_authorization_url(state="test-state", nonce="test-nonce")

        assert "scope=openid+email" in url

    @responses.activate
    def test_exchange_code(self, oidc_config):
        """Test exchanging authorization code for tokens."""
        responses.add(
            responses.GET,
            "https://idp.example.com/.well-known/openid-configuration",
            json=oidc_config,
            status=200,
        )
        responses.add(
            responses.POST,
            "https://idp.example.com/token",
            json={
                "access_token": "test-access-token",
                "id_token": "test-id-token",
                "token_type": "Bearer",
            },
            status=200,
        )

        client = OIDCClient(
            issuer="https://idp.example.com",
            client_id="test-client",
            client_secret="test-secret",
            redirect_uri="https://bridge.example.com/callback",
        )

        tokens = client.exchange_code("auth-code")

        assert tokens["access_token"] == "test-access-token"

        token_request = responses.calls[1].request
        assert "grant_type=authorization_code" in token_request.body
        assert "code=auth-code" in token_request.body
        assert "client_id=test-client" in token_request.body
        assert "client_secret=test-secret" in token_request.body

    @responses.activate
    def test_get_userinfo(self, oidc_config):
        """Test fetching user information."""
        responses.add(
            responses.GET,
            "https://idp.example.com/.well-known/openid-configuration",
            json=oidc_config,
            status=200,
        )
        responses.add(
            responses.GET,
            "https://idp.example.com/userinfo",
            json={
                "sub": "user123",
                "email": "user@example.com",
                "name": "Test User",
                "groups": ["admin"],
            },
            status=200,
        )

        client = OIDCClient(
            issuer="https://idp.example.com",
            client_id="test-client",
            client_secret="test-secret",
            redirect_uri="https://bridge.example.com/callback",
        )

        user_info = client.get_userinfo("test-access-token")

        assert user_info["email"] == "user@example.com"
        assert user_info["name"] == "Test User"

        userinfo_request = responses.calls[1].request
        assert userinfo_request.headers["Authorization"] == "Bearer test-access-token"

    @responses.activate
    def test_issuer_trailing_slash_stripped(self, oidc_config):
        """Test that trailing slash is stripped from issuer."""
        responses.add(
            responses.GET,
            "https://idp.example.com/.well-known/openid-configuration",
            json=oidc_config,
            status=200,
        )

        client = OIDCClient(
            issuer="https://idp.example.com/",
            client_id="test-client",
            client_secret="test-secret",
            redirect_uri="https://bridge.example.com/callback",
        )

        assert client.issuer == "https://idp.example.com"
        _ = client.config
        assert len(responses.calls) == 1
