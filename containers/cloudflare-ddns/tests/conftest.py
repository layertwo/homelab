import pytest
from tests.fixtures.mock_cloudflare import *  # noqa: F401,F403
from tests.fixtures.mock_external_ip import *  # noqa: F401,F403


@pytest.fixture
def zone_id() -> str:
    return "1234"


@pytest.fixture(autouse=True)
def env_vars(monkeypatch, zone_id):
    monkeypatch.setenv("TOKEN", "foobar")
    monkeypatch.setenv("ZONE_ID", zone_id)
    monkeypatch.setenv("DNS_NAME", "example.com")
