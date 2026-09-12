import json
from ipaddress import IPv4Address

import httpx
import pytest
from cloudflare import Cloudflare

from cloudflare_ddns.services.cloudflare_adapter import CloudflareAdapter


@pytest.fixture
def sdk_requests(monkeypatch):
    """Drive the real SDK offline, recording every request the adapter makes.

    The rest of the suite replaces the Cloudflare class with MagicMock, which accepts any
    keyword argument, so it cannot detect a changed or newly-required SDK parameter. Here the
    real client binds the arguments and serialises the request, which is what catches that.
    """
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else {}
        requests.append((request.method, str(request.url), body))
        result = (
            []
            if request.method == "GET"
            else {
                "id": "rec1",
                "name": body["name"],
                "type": body["type"],
                "content": body["content"],
                "proxied": body.get("proxied", False),
                "ttl": body.get("ttl", 1),
            }
        )
        return httpx.Response(
            200, json={"success": True, "errors": [], "messages": [], "result": result}
        )

    client = Cloudflare(
        api_token="dummy",
        base_url="http://mock.local",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    monkeypatch.setattr(
        "cloudflare_ddns.services.cloudflare_adapter.Cloudflare", lambda **kwargs: client
    )
    return requests


def test_writes_bind_against_the_real_sdk(sdk_requests):
    adapter = CloudflareAdapter(api_token="dummy", zone_id="zone1")

    adapter.create_dns_record(dns_name="example.com", ip=IPv4Address("1.1.1.1"))
    adapter.update_dns_record(record_id="rec1", dns_name="example.com", ip=IPv4Address("1.1.1.2"))

    assert [(method, body["ttl"]) for method, _, body in sdk_requests] == [("POST", 1), ("PUT", 1)]


def test_list_is_materialised_so_an_empty_result_is_falsy(sdk_requests):
    adapter = CloudflareAdapter(api_token="dummy", zone_id="zone1")

    records = adapter.get_dns_record(dns_name="example.com", record_type="A")

    assert isinstance(records, list)
    assert not records
