from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_cloudflare_records_list():
    yield MagicMock()


@pytest.fixture
def mock_cloudflare_records_create():
    yield MagicMock()


@pytest.fixture
def mock_cloudflare_records_update():
    yield MagicMock()


@pytest.fixture
def mock_cloudflare_client(
    mock_cloudflare_records_list,
    mock_cloudflare_records_create,
    mock_cloudflare_records_update,
):
    with patch("cloudflare_ddns.services.cloudflare_adapter.Cloudflare") as m:
        m().dns.records.list.side_effect = mock_cloudflare_records_list
        m().dns.records.create.side_effect = mock_cloudflare_records_create
        m().dns.records.update.side_effect = mock_cloudflare_records_update
        yield m
