"""Test search flow functionality."""

import json
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import text

from ethifinx.core.config import Config  # Ensure Config is correctly imported
from ethifinx.db.data_store import DataStore
from ethifinx.db.models import CompanyContext, Universe  # Import your models
from ethifinx.research.search_flow import (
    RateLimitedDDGS,
    call_deepseek_api,
    generate_search_queries,
    get_company_context,
    get_top_companies,
)


@pytest.fixture
def data_store(db_session):
    """Provide a DataStore instance using the test session."""
    return DataStore(session=db_session)


class TestResearchWorkflow:
    """Test research workflow functionality."""

    def test_search_query_generation(self):
        """Test search query generation."""
        mock_queries = [
            {
                "category": "environmental_safety",
                "query": "test query",
                "rationale": "test rationale",
                "priority": 1,
            }
        ]
        with patch("ethifinx.research.search_flow.call_deepseek_api") as mock_api:
            mock_api.return_value = {
                "choices": [{"message": {"content": json.dumps(mock_queries)}}]
            }
            queries = generate_search_queries(
                {"name": "Test Company", "context": "test context"}
            )
            assert len(queries) == 1
            assert queries[0]["category"] == "environmental_safety"

    def test_company_context_generation(self, data_store):
        """Test company context generation."""
        # Insert test data
        test_context = CompanyContext(ticker="TEST", context="test context")
        data_store.save_to_db(test_context)

        context = data_store.get_company_context("TEST")
        assert context.context == "test context"


class TestDatabaseOperations:
    """Test database operations."""

    def test_get_top_companies(self, data_store):
        """Test getting top instruments from database."""
        # Create test data
        instrument = Universe(ticker="TEST", name="Test Company", market_cap=1000000)
        data_store.session.add(instrument)
        data_store.session.commit()

        instruments = data_store.get_top_companies(limit=1)
        assert len(instruments) == 1
        assert instruments[0].name == "Test Company"


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limit_delay(self):
        """Test that rate limiting adds appropriate delay."""
        with patch("time.sleep") as mock_sleep:
            ddgs = RateLimitedDDGS(delay_between_searches=1)
            ddgs._wait_for_rate_limit()
            ddgs._wait_for_rate_limit()
            # Use a more lenient comparison for floating point
            assert mock_sleep.called
            delay = mock_sleep.call_args[0][0]
            assert 0.99 <= delay <= 1.01  # Allow for small variations


class TestErrorHandling:
    """Test error handling."""

    def test_api_timeout(self):
        """Test handling of API timeouts."""
        with patch("ethifinx.research.search_flow.call_deepseek_api") as mock_api:
            mock_api.side_effect = TimeoutError("API timeout")
            with pytest.raises(TimeoutError):
                generate_search_queries({"name": "Test Company", "context": "test"})

    def test_invalid_json_structured_data(self):
        """Test handling of invalid JSON in structured data extraction."""
        with patch("ethifinx.research.search_flow.call_deepseek_api") as mock_api:
            mock_api.return_value = {
                "choices": [{"message": {"content": "invalid json"}}]
            }
            with pytest.raises(ValueError):
                generate_search_queries({"name": "Test Company", "context": "test"})

    @patch("ethifinx.research.search_flow.call_deepseek_api")
    def test_malformed_api_response(self, mock_api, data_store):
        """Test handling of malformed API responses."""
        mock_api.return_value = {"invalid": "response"}
        with pytest.raises(KeyError):
            generate_search_queries({"name": "Test Company", "context": "test"})
