"""Test API client functionality."""

from unittest.mock import Mock, patch

import pytest
from ethifinx.core.api_client import APIClient
from ethifinx.core.config import Config


@pytest.fixture(scope="session")
def test_config() -> Config:
    """
    Provide test configuration.

    Returns
    -------
        Config: Test configuration object.

    """
    return Config(API_BASE_URL="https://api.test.com/v1", API_KEY="test_key")


@pytest.fixture()
def api_client(test_config: Config) -> APIClient:
    """
    Provide API client instance.

    Args:
    ----
        test_config: The test configuration.

    Returns:
    -------
        APIClient: An instance of the API client.

    """
    return APIClient(config=test_config)


@patch("requests.get")
def test_fetch_data_success(mock_get: Mock, api_client: APIClient) -> None:
    """
    Test successful data fetching.

    Args:
    ----
        mock_get: Mocked requests.get method.
        api_client: API client instance.

    """
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
def test_fetch_data_failure(mock_get: Mock, api_client: APIClient) -> None:
    """
    Test data fetching failure.

    Args:
    ----
        mock_get: Mocked requests.get method.
        api_client: API client instance.

    """
    mock_get.side_effect = Exception("API Error")

    with pytest.raises(Exception):
        api_client.fetch_data("/test")


@patch("requests.get")
def test_fetch_data_with_params(mock_get: Mock, api_client: APIClient) -> None:
    """
    Test data fetching with parameters.

    Args:
    ----
        mock_get: Mocked requests.get method.
        api_client: API client instance.

    """
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
def test_fetch_data_invalid_response(mock_get: Mock, api_client: APIClient) -> None:
    """
    Test handling of invalid response.

    Args:
    ----
        mock_get: Mocked requests.get method.
        api_client: API client instance.

    """
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = Exception("Invalid response")
    mock_get.return_value = mock_response

    with pytest.raises(Exception):
        api_client.fetch_data("/test")
