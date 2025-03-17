"""Test API client functionality."""

from unittest.mock import Mock, patch

import pytest

from ethifinx.core.api_client import APIClient
from ethifinx.core.config import Config


@pytest.fixture(scope="session")
def test_config():
    """Provide test configuration."""
    return Config(
        API_BASE_URL="https://api.test.com/v1",
        API_KEY="test_key",
    )


@pytest.fixture
def api_client(test_config):
    """Provide API client instance."""
    return APIClient(config=test_config)


@patch("requests.get")
def test_fetch_data_success(mock_get, api_client):
    """Test successful data fetching."""
    mock_response = Mock()
    mock_response.json.return_value = {"data": "test"}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = api_client.fetch_data("/test")
    assert result == {"data": "test"}
    mock_get.assert_called_with(
        "https://api.test.com/v1/test",
        headers={"Authorization": "Bearer test_key"},
        params=None,
    )


@patch("requests.get")
def test_fetch_data_failure(mock_get, api_client):
    """Test data fetching failure."""
    mock_get.side_effect = Exception("API Error")

    with pytest.raises(Exception):
        api_client.fetch_data("/test")


@patch("requests.get")
def test_fetch_data_with_params(mock_get, api_client):
    """Test data fetching with parameters."""
    mock_response = Mock()
    mock_response.json.return_value = {"data": "test"}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    params = {"key": "value"}
    result = api_client.fetch_data("/test", params=params)
    assert result == {"data": "test"}
    mock_get.assert_called_with(
        "https://api.test.com/v1/test",
        headers={"Authorization": "Bearer test_key"},
        params=params,
    )


@patch("requests.get")
def test_fetch_data_invalid_response(mock_get, api_client):
    """Test handling of invalid response."""
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = Exception("Invalid response")
    mock_get.return_value = mock_response

    with pytest.raises(Exception):
        api_client.fetch_data("/test")
