"""Tests for the SAML module."""

import base64

from lxml import etree

from src.oidc_saml_bridge.saml import SAMLBuilder, parse_authn_request


class TestSAMLBuilder:
    """Tests for SAMLBuilder class."""

    def test_cert_content_loaded(self, temp_certs):
        """Test certificate content is loaded correctly."""
        cert_path, key_path = temp_certs
        builder = SAMLBuilder(
            entity_id="https://bridge.example.com",
            acs_url="https://sp.example.com/acs",
            cert_path=cert_path,
            key_path=key_path,
        )

        cert_content = builder.cert_content
        assert cert_content
        assert "-----BEGIN" not in cert_content
        assert "-----END" not in cert_content

    def test_cert_content_cached(self, temp_certs):
        """Test certificate content is cached."""
        cert_path, key_path = temp_certs
        builder = SAMLBuilder(
            entity_id="https://bridge.example.com",
            acs_url="https://sp.example.com/acs",
            cert_path=cert_path,
            key_path=key_path,
        )

        content1 = builder.cert_content
        content2 = builder.cert_content
        assert content1 is content2

    def test_generate_metadata(self, temp_certs):
        """Test SAML metadata generation."""
        cert_path, key_path = temp_certs
        builder = SAMLBuilder(
            entity_id="https://bridge.example.com",
            acs_url="https://sp.example.com/acs",
            cert_path=cert_path,
            key_path=key_path,
        )

        metadata = builder.generate_metadata("https://bridge.example.com/saml/sso")

        root = etree.fromstring(metadata)
        assert root.get("entityID") == "https://bridge.example.com"

        ns = {"md": "urn:oasis:names:tc:SAML:2.0:metadata"}
        idp_desc = root.find(".//md:IDPSSODescriptor", ns)
        assert idp_desc is not None

        sso_services = root.findall(".//md:SingleSignOnService", ns)
        assert len(sso_services) == 2

    def test_build_response_basic(self, temp_certs):
        """Test building a basic SAML response."""
        cert_path, key_path = temp_certs
        builder = SAMLBuilder(
            entity_id="https://bridge.example.com",
            acs_url="https://sp.example.com/acs",
            cert_path=cert_path,
            key_path=key_path,
        )

        user_info = {
            "email": "user@example.com",
            "name": "Test User",
            "groups": ["admin", "users"],
        }

        response = builder.build_response(user_info)

        decoded = base64.b64decode(response)
        root = etree.fromstring(decoded)

        ns = {
            "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
            "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
        }

        assert root.tag == "{urn:oasis:names:tc:SAML:2.0:protocol}Response"
        assert root.get("Destination") == "https://sp.example.com/acs"

        name_id = root.find(".//saml:NameID", ns)
        assert name_id is not None
        assert name_id.text == "user@example.com"

    def test_build_response_with_request_id(self, temp_certs):
        """Test building a SAML response with InResponseTo."""
        cert_path, key_path = temp_certs
        builder = SAMLBuilder(
            entity_id="https://bridge.example.com",
            acs_url="https://sp.example.com/acs",
            cert_path=cert_path,
            key_path=key_path,
        )

        user_info = {"email": "user@example.com"}
        response = builder.build_response(user_info, request_id="_abc123")

        decoded = base64.b64decode(response)
        root = etree.fromstring(decoded)

        assert root.get("InResponseTo") == "_abc123"

    def test_build_response_with_custom_audience(self, temp_certs):
        """Test building a SAML response with custom audience."""
        cert_path, key_path = temp_certs
        builder = SAMLBuilder(
            entity_id="https://bridge.example.com",
            acs_url="https://sp.example.com/acs",
            cert_path=cert_path,
            key_path=key_path,
        )

        user_info = {"email": "user@example.com"}
        response = builder.build_response(user_info, audience="custom-audience")

        decoded = base64.b64decode(response)
        root = etree.fromstring(decoded)

        ns = {"saml": "urn:oasis:names:tc:SAML:2.0:assertion"}
        audience = root.find(".//saml:Audience", ns)
        assert audience is not None
        assert audience.text == "custom-audience"

    def test_build_response_email_without_at(self, temp_certs):
        """Test RoleSessionName when email has no @ symbol."""
        cert_path, key_path = temp_certs
        builder = SAMLBuilder(
            entity_id="https://bridge.example.com",
            acs_url="https://sp.example.com/acs",
            cert_path=cert_path,
            key_path=key_path,
        )

        user_info = {"email": "testuser"}
        response = builder.build_response(user_info)

        decoded = base64.b64decode(response)
        root = etree.fromstring(decoded)

        ns = {"saml": "urn:oasis:names:tc:SAML:2.0:assertion"}
        attrs = root.findall(".//saml:Attribute", ns)

        role_session_attr = None
        for attr in attrs:
            if "RoleSessionName" in attr.get("Name", ""):
                role_session_attr = attr
                break

        assert role_session_attr is not None
        value = role_session_attr.find("saml:AttributeValue", ns)
        assert value.text == "testuser"

    def test_build_response_with_string_groups(self, temp_certs):
        """Test building a SAML response with groups as string."""
        cert_path, key_path = temp_certs
        builder = SAMLBuilder(
            entity_id="https://bridge.example.com",
            acs_url="https://sp.example.com/acs",
            cert_path=cert_path,
            key_path=key_path,
        )

        user_info = {
            "email": "user@example.com",
            "groups": "admin,users",
        }

        response = builder.build_response(user_info)

        decoded = base64.b64decode(response)
        root = etree.fromstring(decoded)

        ns = {"saml": "urn:oasis:names:tc:SAML:2.0:assertion"}
        attrs = root.findall(".//saml:Attribute", ns)

        groups_attr = None
        for attr in attrs:
            if "groups" in attr.get("Name", ""):
                groups_attr = attr
                break

        assert groups_attr is not None
        value = groups_attr.find("saml:AttributeValue", ns)
        assert value.text == "admin,users"

    def test_build_response_no_groups(self, temp_certs):
        """Test building a SAML response without groups."""
        cert_path, key_path = temp_certs
        builder = SAMLBuilder(
            entity_id="https://bridge.example.com",
            acs_url="https://sp.example.com/acs",
            cert_path=cert_path,
            key_path=key_path,
        )

        user_info = {"email": "user@example.com", "name": "Test User"}
        response = builder.build_response(user_info)

        decoded = base64.b64decode(response)
        root = etree.fromstring(decoded)

        ns = {"saml": "urn:oasis:names:tc:SAML:2.0:assertion"}
        attrs = root.findall(".//saml:Attribute", ns)

        groups_attr = None
        for attr in attrs:
            if "groups" in attr.get("Name", ""):
                groups_attr = attr
                break

        assert groups_attr is None

    def test_build_response_is_signed(self, temp_certs):
        """Test that the SAML response is signed."""
        cert_path, key_path = temp_certs
        builder = SAMLBuilder(
            entity_id="https://bridge.example.com",
            acs_url="https://sp.example.com/acs",
            cert_path=cert_path,
            key_path=key_path,
        )

        user_info = {"email": "user@example.com"}
        response = builder.build_response(user_info)

        decoded = base64.b64decode(response)
        decoded_str = decoded.decode("utf-8")

        assert "ds:Signature" in decoded_str
        assert "ds:SignatureValue" in decoded_str
        assert "ds:X509Certificate" in decoded_str

    def test_build_response_default_name(self, temp_certs):
        """Test that name defaults to email when not provided."""
        cert_path, key_path = temp_certs
        builder = SAMLBuilder(
            entity_id="https://bridge.example.com",
            acs_url="https://sp.example.com/acs",
            cert_path=cert_path,
            key_path=key_path,
        )

        user_info = {"email": "user@example.com"}
        response = builder.build_response(user_info)

        decoded = base64.b64decode(response)
        root = etree.fromstring(decoded)

        ns = {"saml": "urn:oasis:names:tc:SAML:2.0:assertion"}
        attrs = root.findall(".//saml:Attribute", ns)

        name_attr = None
        for attr in attrs:
            if attr.get("Name") == "name":
                name_attr = attr
                break

        assert name_attr is not None
        value = name_attr.find("saml:AttributeValue", ns)
        assert value.text == "user@example.com"


class TestParseAuthnRequest:
    """Tests for parse_authn_request function."""

    def test_parse_valid_request(self):
        """Test parsing a valid SAML AuthnRequest."""
        authn_request = """<?xml version="1.0" encoding="UTF-8"?>
<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="_abc123"
    AssertionConsumerServiceURL="https://sp.example.com/acs">
    <saml:Issuer>https://sp.example.com</saml:Issuer>
</samlp:AuthnRequest>"""

        encoded = base64.b64encode(authn_request.encode()).decode()
        result = parse_authn_request(encoded)

        assert result["id"] == "_abc123"
        assert result["issuer"] == "https://sp.example.com"
        assert result["acs_url"] == "https://sp.example.com/acs"

    def test_parse_invalid_request(self):
        """Test parsing an invalid SAML AuthnRequest."""
        encoded = base64.b64encode(b"not valid xml").decode()
        result = parse_authn_request(encoded)

        assert result["id"] is None
        assert result["issuer"] is None
        assert result["acs_url"] is None

    def test_parse_invalid_base64(self):
        """Test parsing invalid base64."""
        result = parse_authn_request("not-valid-base64!!!")

        assert result["id"] is None
        assert result["issuer"] is None
        assert result["acs_url"] is None
