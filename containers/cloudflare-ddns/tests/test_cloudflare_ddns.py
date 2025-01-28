from unittest.mock import MagicMock

import pytest
from cloudflare.types.dns import AAAARecord, ARecord, PTRRecord

from cloudflare_ddns.main import main


@pytest.fixture
def ip() -> str:
    return "1.1.1.1"


@pytest.fixture
def different_ip() -> str:
    return "1.1.1.2"


@pytest.fixture
def dns_name() -> str:
    return "example.com"


@pytest.fixture
def a_record(ip: str, dns_name: str) -> ARecord:
    return ARecord(id="foobar", content=ip, name=dns_name, type="A", proxied=False)


@pytest.fixture
def aaaa_record(ip: str, dns_name: str) -> AAAARecord:
    return AAAARecord(
        id="foobar",
        content="2001:db8:3333:4444:5555:6666:7777:8888",
        name=dns_name,
        type="AAAA",
    )


@pytest.fixture
def a_record_different(different_ip: str, dns_name) -> ARecord:
    return ARecord(id="foobar", content=different_ip, name=dns_name, type="A")


@pytest.fixture
def ptr_record(different_ip: str, dns_name) -> PTRRecord:
    return PTRRecord(id="foobar", content=different_ip, name=dns_name, type="PTR")


@pytest.fixture
def mock_requests_response(ip):
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"ip": ip}
    return response


def test_happy_path_same_ip(
    mock_requests_get,
    mock_requests_response,
    mock_cloudflare_client,
    mock_cloudflare_records_list,
    a_record,
):
    mock_requests_get.return_value = mock_requests_response
    mock_cloudflare_records_list.return_value = [a_record]
    main()


def test_happy_path_with_proxy(
    monkeypatch,
    mock_requests_get,
    mock_requests_response,
    mock_cloudflare_client,
    mock_cloudflare_records_list,
    a_record,
):
    monkeypatch.setenv("ENABLE_PROXY", "TRUE")
    mock_requests_get.return_value = mock_requests_response
    mock_cloudflare_records_list.return_value = [a_record]
    main()


def test_happy_path_no_ip(
    mock_requests_get,
    mock_requests_response,
    mock_cloudflare_client,
    mock_cloudflare_records_list,
    a_record,
):
    mock_requests_get.return_value = mock_requests_response
    mock_cloudflare_records_list.return_value = None
    main()


def test_happy_path_different_ip(
    mock_requests_get,
    mock_requests_response,
    mock_cloudflare_client,
    mock_cloudflare_records_list,
    mock_cloudflare_records_update,
    a_record_different,
    zone_id,
    dns_name,
    different_ip,
):
    mock_requests_get.return_value = mock_requests_response
    mock_cloudflare_records_list.return_value = [a_record_different]
    # mock_cloudflare_records_update.assert_called_with(a_record_id=a_record_different.id, zone_id=zone_id, dns_name=dns_name, type=a_record_different.type, context=different_ip, proxied=False)
    main()


def test_happy_path_wrong_record_type(
    mock_requests_get,
    mock_requests_response,
    mock_cloudflare_client,
    mock_cloudflare_records_list,
    ptr_record,
):
    mock_requests_get.return_value = mock_requests_response
    mock_cloudflare_records_list.return_value = [ptr_record]
    main()


def test_happy_path_mismatched_record_type(
    mock_requests_get,
    mock_requests_response,
    mock_cloudflare_client,
    mock_cloudflare_records_list,
    aaaa_record,
):
    mock_requests_get.return_value = mock_requests_response
    mock_cloudflare_records_list.return_value = [aaaa_record]
    main()
