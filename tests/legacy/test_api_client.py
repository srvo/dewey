
# Refactored from: test_api_client
# Date: 2025-03-16T16:19:08.178644
# Refactor Version: 1.0
"""Tests for the API client."""

from unittest.mock import MagicMock, patch

import pytest
from email_processing.api_client import APIClient


@pytest.fixture
def mock_session():
    session = MagicMock()
    session.headers = {}
    return session


def test_fetch_data_success(mock_session) -> None:
    """Test successful data fetching."""
    with patch("requests.Session", return_value=mock_session):
        client = APIClient(base_url="http://test.com", api_key="test_key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_session.get.return_value = mock_response

        response = client.fetch_data("/test")
        assert response == {"data": "test"}
        mock_session.get.assert_called_once_with("http://test.com/test", params=None)


def test_fetch_data_failure(mock_session) -> None:
    """Test failed data fetching."""
    with patch("requests.Session", return_value=mock_session):
        client = APIClient(base_url="http://test.com", api_key="test_key")

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("API request failed")
        mock_session.get.return_value = mock_response

        with pytest.raises(Exception, match="API request failed"):
            client.fetch_data("/test")
        mock_session.get.assert_called_once_with("http://test.com/test", params=None)


def test_post_data_success(mock_session) -> None:
    """Test successful data posting."""
    with patch("requests.Session", return_value=mock_session):
        client = APIClient(base_url="http://test.com", api_key="test_key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_session.post.return_value = mock_response

        response = client.post_data("/test", {"key": "value"})
        assert response == {"status": "success"}
        mock_session.post.assert_called_once_with(
            "http://test.com/test",
            json={"key": "value"},
        )


def test_post_data_failure(mock_session) -> None:
    """Test failed data posting."""
    with patch("requests.Session", return_value=mock_session):
        client = APIClient(base_url="http://test.com", api_key="test_key")

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("API request failed")
        mock_session.post.return_value = mock_response

        with pytest.raises(Exception, match="API request failed"):
            client.post_data("/test", {"key": "value"})
        mock_session.post.assert_called_once_with(
            "http://test.com/test",
            json={"key": "value"},
        )
