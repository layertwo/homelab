"""Tests for the Flask application."""

import base64

import pytest
import responses
from lxml import etree

from src.oidc_saml_bridge.app import create_app


class TestApp:
    """Tests for the Flask application."""

    @pytest.fixture
    def oidc_config(self):
        """OIDC discovery configuration fixture."""
        return {
            "issuer": "https://idp.example.com",
            "authorization_endpoint": "https://idp.example.com/authorize",
            "token_endpoint": "https://idp.example.com/token",
            "userinfo_endpoint": "https://idp.example.com/userinfo",
        }

    @pytest.fixture
    def app(self, service_provider):
        """Create test Flask application."""
        return create_app(service_provider=service_provider)

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    @responses.activate
    def test_health_endpoint(self, client, oidc_config):
        """Test health check endpoint."""
        responses.add(
            responses.GET,
            "https://idp.example.com/.well-known/openid-configuration",
            json=oidc_config,
            status=200,
        )
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json == {"status": "healthy"}

    @responses.activate
    def test_saml_metadata_endpoint(self, client, oidc_config):
        """Test SAML metadata endpoint."""
        responses.add(
            responses.GET,
            "https://idp.example.com/.well-known/openid-configuration",
            json=oidc_config,
            status=200,
        )

        response = client.get("/saml/metadata")

        assert response.status_code == 200
        assert response.content_type == "application/xml"

        root = etree.fromstring(response.data)
        assert root.get("entityID") == "https://bridge.example.com"

    @responses.activate
    def test_saml_sso_redirect(self, client, oidc_config):
        """Test SAML SSO redirects to OIDC provider."""
        responses.add(
            responses.GET,
            "https://idp.example.com/.well-known/openid-configuration",
            json=oidc_config,
            status=200,
        )

        response = client.post("/saml/sso")

        assert response.status_code == 302
        assert "https://idp.example.com/authorize" in response.location
        assert "response_type=code" in response.location
        assert "client_id=test-client" in response.location

    @responses.activate
    def test_saml_sso_with_authn_request(self, client, oidc_config):
        """Test SAML SSO with AuthnRequest."""
        responses.add(
            responses.GET,
            "https://idp.example.com/.well-known/openid-configuration",
            json=oidc_config,
            status=200,
        )

        authn_request = """<?xml version="1.0" encoding="UTF-8"?>
<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="_request123"
    AssertionConsumerServiceURL="https://sp.example.com/acs">
    <saml:Issuer>https://sp.example.com</saml:Issuer>
</samlp:AuthnRequest>"""

        encoded_request = base64.b64encode(authn_request.encode()).decode()

        response = client.post(f"/saml/sso?SAMLRequest={encoded_request}&RelayState=test-relay")

        assert response.status_code == 302
        assert "https://idp.example.com/authorize" in response.location

    @responses.activate
    def test_callback_success(self, client, oidc_config):
        """Test successful OIDC callback."""
        responses.add(
            responses.GET,
            "https://idp.example.com/.well-known/openid-configuration",
            json=oidc_config,
            status=200,
        )
        responses.add(
            responses.POST,
            "https://idp.example.com/token",
            json={"access_token": "test-token", "token_type": "Bearer"},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://idp.example.com/userinfo",
            json={
                "sub": "user123",
                "email": "user@example.com",
                "name": "Test User",
            },
            status=200,
        )

        with client.session_transaction() as sess:
            sess["oidc_state"] = "test-state"
            sess["oidc_nonce"] = "test-nonce"
            sess["saml_request_id"] = "_request123"
            sess["relay_state"] = "test-relay"

        response = client.get("/callback?code=auth-code&state=test-state")

        assert response.status_code == 200
        assert b"SAMLResponse" in response.data
        assert b"test-relay" in response.data
        assert b'action="https://sp.example.com/saml/acs"' in response.data

    @responses.activate
    def test_callback_error_from_provider(self, client, oidc_config):
        """Test callback with error from OIDC provider."""
        responses.add(
            responses.GET,
            "https://idp.example.com/.well-known/openid-configuration",
            json=oidc_config,
            status=200,
        )

        response = client.get(
            "/callback?error=access_denied&error_description=User%20denied%20access"
        )

        assert response.status_code == 400
        assert response.json["error"] == "access_denied"

    @responses.activate
    def test_callback_missing_code(self, client, oidc_config):
        """Test callback without authorization code."""
        responses.add(
            responses.GET,
            "https://idp.example.com/.well-known/openid-configuration",
            json=oidc_config,
            status=200,
        )

        response = client.get("/callback?state=test-state")

        assert response.status_code == 400
        assert response.json["error"] == "missing_code"

    @responses.activate
    def test_callback_state_mismatch(self, client, oidc_config):
        """Test callback with state mismatch."""
        responses.add(
            responses.GET,
            "https://idp.example.com/.well-known/openid-configuration",
            json=oidc_config,
            status=200,
        )

        with client.session_transaction() as sess:
            sess["oidc_state"] = "correct-state"

        response = client.get("/callback?code=auth-code&state=wrong-state")

        assert response.status_code == 400
        assert response.json["error"] == "invalid_state"

    @responses.activate
    def test_callback_no_access_token(self, client, oidc_config):
        """Test callback when token response has no access token."""
        responses.add(
            responses.GET,
            "https://idp.example.com/.well-known/openid-configuration",
            json=oidc_config,
            status=200,
        )
        responses.add(
            responses.POST,
            "https://idp.example.com/token",
            json={"token_type": "Bearer"},
            status=200,
        )

        with client.session_transaction() as sess:
            sess["oidc_state"] = "test-state"

        response = client.get("/callback?code=auth-code&state=test-state")

        assert response.status_code == 400
        assert response.json["error"] == "no_token"

    @responses.activate
    def test_health_endpoint_unhealthy(self, client):
        """Test health check endpoint when OIDC provider is unreachable."""
        responses.add(
            responses.GET,
            "https://idp.example.com/.well-known/openid-configuration",
            status=500,
        )

        response = client.get("/health")

        assert response.status_code == 503
        assert response.json["status"] == "unhealthy"

    @responses.activate
    def test_saml_sso_provider_error(self, client, oidc_config):
        """Test SAML SSO when OIDC provider is unreachable."""
        responses.add(
            responses.GET,
            "https://idp.example.com/.well-known/openid-configuration",
            status=500,
        )

        response = client.get("/saml/sso")

        assert response.status_code == 502
        assert response.json["error"] == "provider_error"

    @responses.activate
    def test_callback_exchange_code_value_error(self, client, oidc_config):
        """Test callback when exchange_code raises ValueError."""
        import jwt

        # Create a JWT with wrong nonce
        id_token = jwt.encode(
            {"sub": "user123", "nonce": "wrong-nonce", "aud": "test-client"},
            "secret",
            algorithm="HS256",
        )

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
                "id_token": id_token,
                "token_type": "Bearer",
            },
            status=200,
        )

        with client.session_transaction() as sess:
            sess["oidc_state"] = "test-state"
            sess["oidc_nonce"] = "test-nonce"

        response = client.get("/callback?code=auth-code&state=test-state")

        assert response.status_code == 400
        assert response.json["error"] == "invalid_token"

    @responses.activate
    def test_callback_exchange_code_http_error(self, client, oidc_config):
        """Test callback when token endpoint returns HTTP error."""
        responses.add(
            responses.GET,
            "https://idp.example.com/.well-known/openid-configuration",
            json=oidc_config,
            status=200,
        )
        responses.add(
            responses.POST,
            "https://idp.example.com/token",
            status=400,
        )

        with client.session_transaction() as sess:
            sess["oidc_state"] = "test-state"

        response = client.get("/callback?code=auth-code&state=test-state")

        assert response.status_code == 502
        assert response.json["error"] == "token_exchange_failed"

    @responses.activate
    def test_callback_exchange_code_request_exception(self, client, oidc_config):
        """Test callback when token endpoint is unreachable."""
        import requests as req

        responses.add(
            responses.GET,
            "https://idp.example.com/.well-known/openid-configuration",
            json=oidc_config,
            status=200,
        )
        responses.add(
            responses.POST,
            "https://idp.example.com/token",
            body=req.exceptions.ConnectionError("Connection error"),
        )

        with client.session_transaction() as sess:
            sess["oidc_state"] = "test-state"

        response = client.get("/callback?code=auth-code&state=test-state")

        assert response.status_code == 502
        assert response.json["error"] == "provider_error"

    @responses.activate
    def test_callback_userinfo_http_error(self, client, oidc_config):
        """Test callback when userinfo endpoint returns HTTP error."""
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
                "token_type": "Bearer",
            },
            status=200,
        )
        responses.add(
            responses.GET,
            "https://idp.example.com/userinfo",
            status=403,
        )

        with client.session_transaction() as sess:
            sess["oidc_state"] = "test-state"

        response = client.get("/callback?code=auth-code&state=test-state")

        assert response.status_code == 502
        assert response.json["error"] == "userinfo_failed"

    @responses.activate
    def test_callback_userinfo_request_exception(self, client, oidc_config):
        """Test callback when userinfo endpoint is unreachable."""
        import requests as req

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
                "token_type": "Bearer",
            },
            status=200,
        )
        responses.add(
            responses.GET,
            "https://idp.example.com/userinfo",
            body=req.exceptions.ConnectionError("Connection error"),
        )

        with client.session_transaction() as sess:
            sess["oidc_state"] = "test-state"

        response = client.get("/callback?code=auth-code&state=test-state")

        assert response.status_code == 502
        assert response.json["error"] == "provider_error"

    @responses.activate
    def test_callback_userinfo_unexpected_exception(
        self, service_provider, oidc_config, monkeypatch
    ):
        """Test callback when userinfo fetching raises unexpected exception."""
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
                "token_type": "Bearer",
            },
            status=200,
        )

        # Mock get_userinfo to raise an unexpected exception
        def failing_get_userinfo(*args, **kwargs):
            raise KeyError("Unexpected error in userinfo processing")

        monkeypatch.setattr(service_provider.oidc_client, "get_userinfo", failing_get_userinfo)

        app = create_app(service_provider=service_provider)
        test_client = app.test_client()

        with test_client.session_transaction() as sess:
            sess["oidc_state"] = "test-state"

        response = test_client.get("/callback?code=auth-code&state=test-state")

        assert response.status_code == 500
        assert response.json["error"] == "userinfo_error"
        assert "Unexpected error" in response.json["description"]

    @responses.activate
    def test_callback_saml_build_error(self, service_provider, oidc_config, monkeypatch):
        """Test callback when SAML response building fails."""
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
                "token_type": "Bearer",
            },
            status=200,
        )
        responses.add(
            responses.GET,
            "https://idp.example.com/userinfo",
            json={
                "sub": "user123",
                "email": "user@example.com",
                "name": "Test User",
            },
            status=200,
        )

        # Mock build_response to raise an exception
        def failing_build(*args, **kwargs):
            raise Exception("SAML build error")

        monkeypatch.setattr(service_provider.saml_builder, "build_response", failing_build)

        app = create_app(service_provider=service_provider)
        test_client = app.test_client()

        with test_client.session_transaction() as sess:
            sess["oidc_state"] = "test-state"

        response = test_client.get("/callback?code=auth-code&state=test-state")

        assert response.status_code == 500
        assert response.json["error"] == "saml_build_failed"
