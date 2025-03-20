import pytest
from unittest.mock import patch
from dewey.core.engines.duckduckgo import DuckDuckGo
from dewey.core.base_script import BaseScript
import logging
from typing import Any


class TestDuckDuckGo:
    """
    Comprehensive unit tests for the DuckDuckGo class.
    """

    @pytest.fixture
    def duckduckgo(self) -> DuckDuckGo:
        """
        Pytest fixture to create an instance of the DuckDuckGo class.

        Returns:
            An instance of the DuckDuckGo class.
        """
        return DuckDuckGo()

    def test_duckduckgo_initialization(self, duckduckgo: DuckDuckGo) -> None:
        """
        Test the initialization of the DuckDuckGo class.
        """
        assert isinstance(duckduckgo, DuckDuckGo)
        assert isinstance(duckduckgo, BaseScript)
        assert duckduckgo.name == "DuckDuckGo"
        assert duckduckgo.config_section == "duckduckgo"

    @patch("dewey.core.engines.duckduckgo.DuckDuckGo.get_config_value")
    @patch("dewey.core.engines.duckduckgo.DuckDuckGo.search")
    def test_run(
        self,
        mock_search: Any,
        mock_get_config_value: Any,
        duckduckgo: DuckDuckGo,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        Test the run method of the DuckDuckGo class.

        This test mocks the get_config_value and search methods to isolate
        the run method's logic.

        Args:
            mock_search: Mocked search method.
            mock_get_config_value: Mocked get_config_value method.
            duckduckgo: DuckDuckGo fixture instance.
            caplog: pytest caplog fixture for capturing log messages.
        """
        mock_get_config_value.return_value = "test_query"
        mock_search.return_value = "test_results"
        caplog.set_level(logging.INFO)

        duckduckgo.run()

        mock_get_config_value.assert_called_with("query", "default_query")
        mock_search.assert_called_with("test_query")
        assert "Searching DuckDuckGo for: test_query" in caplog.text
        assert "Results: test_results" in caplog.text

    def test_search(self, duckduckgo: DuckDuckGo) -> None:
        """
        Test the search method of the DuckDuckGo class.

        Args:
            duckduckgo: DuckDuckGo fixture instance.
        """
        query = "test_query"
        results = duckduckgo.search(query)
        assert results == f"DuckDuckGo search results for: {query}"

    def test_search_empty_query(self, duckduckgo: DuckDuckGo) -> None:
        """
        Test the search method with an empty query.

        Args:
            duckduckgo: DuckDuckGo fixture instance.
        """
        query = ""
        results = duckduckgo.search(query)
        assert results == f"DuckDuckGo search results for: {query}"

    def test_search_special_characters(self, duckduckgo: DuckDuckGo) -> None:
        """
        Test the search method with special characters in the query.

        Args:
            duckduckgo: DuckDuckGo fixture instance.
        """
        query = "!@#$%^&*()"
        results = duckduckgo.search(query)
        assert results == f"DuckDuckGo search results for: {query}"
