"""Flask application for the OIDC to SAML bridge."""

import secrets
from typing import Any, Optional

from flask import Flask, redirect, request, session

from oidc_saml_bridge.environment import ServiceProvider
from oidc_saml_bridge.saml import parse_authn_request


def create_app(service_provider: Optional[ServiceProvider] = None) -> Flask:
    """Create and configure the Flask application."""
    if not service_provider:  # pragma: no cover
        service_provider = ServiceProvider()
    app = Flask(__name__)

    app.config["SECRET_KEY"] = service_provider.secret_key
    app.config["SESSION_COOKIE_SECURE"] = service_provider.session_cookie_secure
    app.config["SESSION_COOKIE_HTTPONLY"] = service_provider.session_cookie_httponly
    app.config["SESSION_COOKIE_SAMESITE"] = service_provider.session_cookie_samesite

    saml_builder = service_provider.saml_builder
    oidc_client = service_provider.oidc_client
    saml_audience = service_provider.saml_audience

    @app.route("/health")
    def health() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    @app.route("/saml/metadata")
    def saml_metadata() -> Any:
        """Return SAML IdP metadata."""
        sso_url = request.url_root.rstrip("/") + "/saml/sso"
        metadata = saml_builder.generate_metadata(sso_url)
        return metadata, 200, {"Content-Type": "application/xml"}

    @app.route("/saml/sso", methods=["GET", "POST"])
    def saml_sso() -> Any:
        """Handle SAML AuthnRequest and redirect to OIDC provider."""
        saml_request = request.args.get("SAMLRequest")
        relay_state = request.args.get("RelayState", "")

        request_data = {"id": None, "issuer": None, "acs_url": None}
        if saml_request:
            request_data = parse_authn_request(saml_request)

        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)

        session["saml_request_id"] = request_data.get("id")
        session["relay_state"] = relay_state
        session["oidc_state"] = state
        session["oidc_nonce"] = nonce

        auth_url = oidc_client.get_authorization_url(state, nonce)
        return redirect(auth_url)

    @app.route("/callback")
    def callback() -> Any:
        """Handle OIDC callback and return SAML response."""
        code = request.args.get("code")
        state = request.args.get("state")
        error = request.args.get("error")

        if error:
            return {"error": error, "description": request.args.get("error_description")}, 400

        if not code:
            return {"error": "missing_code", "description": "No authorization code provided"}, 400

        if state != session.get("oidc_state"):
            return {"error": "invalid_state", "description": "State mismatch"}, 400

        tokens = oidc_client.exchange_code(code)
        access_token = tokens.get("access_token")

        if not access_token:
            return {"error": "no_token", "description": "No access token received"}, 400

        user_info = oidc_client.get_userinfo(access_token)

        saml_request_id = session.get("saml_request_id")
        relay_state = session.get("relay_state", "")

        saml_response = saml_builder.build_response(
            user_info=user_info,
            request_id=saml_request_id,
            audience=saml_audience,
        )

        session.clear()

        return (
            f"""
<!DOCTYPE html>
<html>
<head><title>SAML Response</title></head>
<body onload="document.forms[0].submit()">
<noscript><p>JavaScript is required. Please click the button below.</p></noscript>
<form method="POST" action="{service_provider.saml_acs_url}">
<input type="hidden" name="SAMLResponse" value="{saml_response}"/>
<input type="hidden" name="RelayState" value="{relay_state}"/>
<noscript><input type="submit" value="Continue"/></noscript>
</form>
</body>
</html>
""",
            200,
            {"Content-Type": "text/html"},
        )

    return app


def main() -> None:  # pragma: nocover
    """Entry point for the application."""
    service_provider = ServiceProvider()
    app = create_app(service_provider=service_provider)
    app.run(host="0.0.0.0", port=8080, debug=service_provider.debug)


if __name__ == "__main__":  # pragma: nocover
    main()
