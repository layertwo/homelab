"""SAML assertion and metadata generation."""

import base64
import uuid
from datetime import datetime, timedelta, timezone
from functools import cached_property
from typing import Any

from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.x509 import load_pem_x509_certificate
from lxml import etree
from signxml import XMLSigner
from signxml.algorithms import (
    CanonicalizationMethod,
    DigestAlgorithm,
    SignatureConstructionMethod,
    SignatureMethod,
)
from signxml.util import strip_pem_header

SAML_NS = "urn:oasis:names:tc:SAML:2.0:assertion"
SAMLP_NS = "urn:oasis:names:tc:SAML:2.0:protocol"
MD_NS = "urn:oasis:names:tc:SAML:2.0:metadata"
DS_NS = "http://www.w3.org/2000/09/xmlsig#"

NSMAP = {
    "saml": SAML_NS,
    "samlp": SAMLP_NS,
    "md": MD_NS,
    "ds": DS_NS,
}

NAME_ID_FORMAT = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
BINDING_POST = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
BINDING_REDIRECT = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"


class SAMLBuilder:
    """Builds and signs SAML assertions and metadata."""

    def __init__(self, entity_id: str, acs_url: str, cert_path: str, key_path: str) -> None:
        self.entity_id = entity_id
        self.acs_url = acs_url
        self.cert_path = cert_path
        self.key_path = key_path

    @cached_property
    def cert_content(self) -> str:
        """Load and cache certificate content (base64 without headers)."""
        with open(self.cert_path, "rb") as f:
            cert_pem = f.read()
        return strip_pem_header(cert_pem.decode("utf-8"))

    @cached_property
    def key_content(self) -> bytes:
        """Load and cache private key content."""
        with open(self.key_path, "rb") as f:
            return f.read()

    @cached_property
    def cert_bytes(self) -> bytes:
        """Load and cache certificate bytes."""
        with open(self.cert_path, "rb") as f:
            return f.read()

    def generate_metadata(self, sso_url: str) -> bytes:
        """Generate SAML IdP metadata XML."""
        root = etree.Element(
            "{%s}EntityDescriptor" % MD_NS,
            nsmap={"md": MD_NS, "ds": DS_NS},
            entityID=self.entity_id,
        )

        idp_descriptor = etree.SubElement(
            root,
            "{%s}IDPSSODescriptor" % MD_NS,
            WantAuthnRequestsSigned="false",
            protocolSupportEnumeration=SAMLP_NS,
        )

        key_descriptor = etree.SubElement(
            idp_descriptor, "{%s}KeyDescriptor" % MD_NS, use="signing"
        )
        key_info = etree.SubElement(key_descriptor, "{%s}KeyInfo" % DS_NS)
        x509_data = etree.SubElement(key_info, "{%s}X509Data" % DS_NS)
        x509_cert = etree.SubElement(x509_data, "{%s}X509Certificate" % DS_NS)
        x509_cert.text = self.cert_content

        etree.SubElement(
            idp_descriptor,
            "{%s}NameIDFormat" % MD_NS,
        ).text = NAME_ID_FORMAT

        etree.SubElement(
            idp_descriptor,
            "{%s}SingleSignOnService" % MD_NS,
            Binding=BINDING_REDIRECT,
            Location=sso_url,
        )

        etree.SubElement(
            idp_descriptor,
            "{%s}SingleSignOnService" % MD_NS,
            Binding=BINDING_POST,
            Location=sso_url,
        )

        return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8")

    def build_response(
        self,
        user_info: dict[str, Any],
        request_id: str | None = None,
        audience: str | None = None,
    ) -> str:
        """Build a signed SAML response with assertion."""
        now = datetime.now(timezone.utc)
        response_id = "_" + str(uuid.uuid4())
        assertion_id = "_" + str(uuid.uuid4())
        not_before = now - timedelta(minutes=5)
        not_on_or_after = now + timedelta(minutes=15)
        session_not_on_or_after = now + timedelta(hours=8)

        if audience is None:
            audience = self.acs_url

        email = user_info.get("email", "")
        name = user_info.get("name", email)
        groups = user_info.get("groups", [])

        root = etree.Element(
            "{%s}Response" % SAMLP_NS,
            nsmap={"samlp": SAMLP_NS, "saml": SAML_NS},
            ID=response_id,
            Version="2.0",
            IssueInstant=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            Destination=self.acs_url,
        )
        if request_id:
            root.set("InResponseTo", request_id)

        issuer = etree.SubElement(root, "{%s}Issuer" % SAML_NS)
        issuer.text = self.entity_id

        status = etree.SubElement(root, "{%s}Status" % SAMLP_NS)
        etree.SubElement(
            status,
            "{%s}StatusCode" % SAMLP_NS,
            Value="urn:oasis:names:tc:SAML:2.0:status:Success",
        )

        assertion = etree.SubElement(
            root,
            "{%s}Assertion" % SAML_NS,
            nsmap={"saml": SAML_NS},
            ID=assertion_id,
            Version="2.0",
            IssueInstant=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

        assertion_issuer = etree.SubElement(assertion, "{%s}Issuer" % SAML_NS)
        assertion_issuer.text = self.entity_id

        subject = etree.SubElement(assertion, "{%s}Subject" % SAML_NS)
        name_id = etree.SubElement(
            subject,
            "{%s}NameID" % SAML_NS,
            Format=NAME_ID_FORMAT,
        )
        name_id.text = email

        subject_confirmation = etree.SubElement(
            subject,
            "{%s}SubjectConfirmation" % SAML_NS,
            Method="urn:oasis:names:tc:SAML:2.0:cm:bearer",
        )
        subject_confirmation_data = etree.SubElement(
            subject_confirmation,
            "{%s}SubjectConfirmationData" % SAML_NS,
            NotOnOrAfter=not_on_or_after.strftime("%Y-%m-%dT%H:%M:%SZ"),
            Recipient=self.acs_url,
        )
        if request_id:
            subject_confirmation_data.set("InResponseTo", request_id)

        conditions = etree.SubElement(
            assertion,
            "{%s}Conditions" % SAML_NS,
            NotBefore=not_before.strftime("%Y-%m-%dT%H:%M:%SZ"),
            NotOnOrAfter=not_on_or_after.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        audience_restriction = etree.SubElement(conditions, "{%s}AudienceRestriction" % SAML_NS)
        audience_elem = etree.SubElement(audience_restriction, "{%s}Audience" % SAML_NS)
        audience_elem.text = audience

        authn_statement = etree.SubElement(
            assertion,
            "{%s}AuthnStatement" % SAML_NS,
            AuthnInstant=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            SessionIndex=assertion_id,
            SessionNotOnOrAfter=session_not_on_or_after.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        authn_context = etree.SubElement(authn_statement, "{%s}AuthnContext" % SAML_NS)
        authn_context_class_ref = etree.SubElement(
            authn_context, "{%s}AuthnContextClassRef" % SAML_NS
        )
        authn_context_class_ref.text = (
            "urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport"
        )

        attribute_statement = etree.SubElement(assertion, "{%s}AttributeStatement" % SAML_NS)

        self._add_attribute(
            attribute_statement,
            "https://aws.amazon.com/SAML/Attributes/RoleSessionName",
            email.split("@")[0] if "@" in email else email,
        )
        self._add_attribute(attribute_statement, "email", email)
        self._add_attribute(attribute_statement, "name", name)

        if groups:
            self._add_attribute(
                attribute_statement,
                "https://aws.amazon.com/SAML/Attributes/PrincipalTag:groups",
                ",".join(groups) if isinstance(groups, list) else groups,
            )

        signed_assertion = self._sign_assertion(assertion)

        root.remove(assertion)
        root.append(signed_assertion)

        return base64.b64encode(
            etree.tostring(root, xml_declaration=True, encoding="UTF-8")
        ).decode("utf-8")

    def _add_attribute(self, parent: etree._Element, name: str, value: str) -> etree._Element:
        """Add a SAML attribute to the attribute statement."""
        attr = etree.SubElement(
            parent,
            "{%s}Attribute" % SAML_NS,
            Name=name,
            NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:uri",
        )
        attr_value = etree.SubElement(attr, "{%s}AttributeValue" % SAML_NS)
        attr_value.text = value
        return attr

    def _sign_assertion(self, assertion: etree._Element) -> etree._Element:
        """Sign the SAML assertion using XML signature."""
        cert = load_pem_x509_certificate(self.cert_bytes)

        signer = XMLSigner(
            method=SignatureConstructionMethod.enveloped,
            signature_algorithm=SignatureMethod.RSA_SHA256,
            digest_algorithm=DigestAlgorithm.SHA256,
            c14n_algorithm=CanonicalizationMethod.EXCLUSIVE_XML_CANONICALIZATION_1_0,
        )

        signed_assertion = signer.sign(
            assertion,
            key=self.key_content,
            cert=cert.public_bytes(Encoding.PEM),
            reference_uri="#" + assertion.get("ID"),
        )

        return signed_assertion


def parse_authn_request(encoded_request: str) -> dict[str, str | None]:
    """Parse a SAML AuthnRequest and extract relevant fields."""
    try:
        decoded = base64.b64decode(encoded_request)
        root = etree.fromstring(decoded)
        return {
            "id": root.get("ID"),
            "issuer": root.findtext("{%s}Issuer" % SAML_NS),
            "acs_url": root.get("AssertionConsumerServiceURL"),
        }
    except Exception:
        return {"id": None, "issuer": None, "acs_url": None}
