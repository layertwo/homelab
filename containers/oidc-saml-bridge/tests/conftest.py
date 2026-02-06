"""Pytest fixtures for oidc-saml-bridge tests."""

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from oidc_saml_bridge.environment import ServiceProvider


@pytest.fixture
def temp_certs():
    """Generate temporary RSA key pair and certificate for testing."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, "test.example.com"),
        ]
    )

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
        .sign(private_key, hashes.SHA256())
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        key_path = Path(tmpdir) / "saml.key"
        cert_path = Path(tmpdir) / "saml.crt"

        key_path.write_bytes(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

        cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))

        yield str(cert_path), str(key_path)


@pytest.fixture(autouse=True)
def environment(temp_certs, monkeypatch):
    """Set up environment variables for config testing."""
    cert_path, key_path = temp_certs
    monkeypatch.setenv("BRIDGE_URL", "https://bridge.example.com")
    monkeypatch.setenv("OIDC_ISSUER", "https://idp.example.com")
    monkeypatch.setenv("OIDC_CLIENT_ID", "test-client")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("OIDC_REDIRECT_URI", "https://bridge.example.com/callback")
    monkeypatch.setenv("SAML_ENTITY_ID", "https://bridge.example.com")
    monkeypatch.setenv("SAML_ACS_URL", "https://sp.example.com/saml/acs")
    monkeypatch.setenv("SAML_AUDIENCE", "https://us-east-1.signin.aws/platform/saml/d-test123")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("CERT_PATH", cert_path)
    monkeypatch.setenv("KEY_PATH", key_path)
    return cert_path, key_path


@pytest.fixture
def service_provider():
    return ServiceProvider()
