from unittest.mock import patch

import pytest


@pytest.fixture
def mock_requests_get():
    with patch("requests.get") as mock_get:
        yield mock_get
