"""Tests for dewey.core.architecture.analyze_architecture."""

import logging
from unittest.mock import patch, MagicMock
from typing import Dict, List, Any, Optional

import pytest

from dewey.core.base_script import BaseScript
from dewey.core.architecture.analyze_architecture import AnalyzeArchitecture, DatabaseConnectionInterface, LLMClientInterface
from dewey.core.db.connection import DatabaseConnection
from dewey.llm.llm_utils import LLMClient


class MockDatabaseConnection:
    """Mock class for DatabaseConnectionInterface."""

    def execute(self, query: str) -> None:
        """Mock execute method."""
        pass


class MockLLMClient:
    """Mock class for LLMClientInterface."""

    def generate_text(self, prompt: str) -> str:
        """Mock generate_text method."""
        return "Mock LLM Response"


class TestAnalyzeArchitecture:
    """Unit tests for the AnalyzeArchitecture class."""

    @pytest.fixture
    def mock_base_script(self) -> MagicMock:
        """Fixture to mock BaseScript instance."""
        mock_script = MagicMock(spec=BaseScript)
        mock_script.get_config_value.return_value = "test_value"
        mock_script.logger = MagicMock()
        return mock_script

    @pytest.fixture
    def mock_db_connection(self) -> MockDatabaseConnection:
        """Fixture to create a mock database connection."""
        return MockDatabaseConnection()

    @pytest.fixture
    def mock_llm_client(self) -> MockLLMClient:
        """Fixture to create a mock LLM client."""
        return MockLLMClient()

    @pytest.fixture
    def analyzer(self, mock_db_connection: MockDatabaseConnection, mock_llm_client: MockLLMClient) -> AnalyzeArchitecture:
        """Fixture to create an instance of AnalyzeArchitecture with mocked dependencies."""
        with patch("dewey.core.architecture.analyze_architecture.BaseScript.__init__", return_value=None):
            analyzer = AnalyzeArchitecture(db_connection=mock_db_connection, llm_client=mock_llm_client)
            analyzer.logger = MagicMock()
            analyzer.config = {}
            return analyzer

    def test_init(self, analyzer: AnalyzeArchitecture) -> None:
        """Test the initialization of the AnalyzeArchitecture class."""
        assert analyzer.name == "AnalyzeArchitecture"
        assert analyzer.description is None
        assert analyzer.config_section == "analyze_architecture"
        assert analyzer.requires_db is True
        assert analyzer.enable_llm is True

    def test_get_db_connection_uses_provided_connection(self, analyzer: AnalyzeArchitecture, mock_db_connection: MockDatabaseConnection) -> None:
        """Test that _get_db_connection returns the provided connection if available."""
        assert analyzer._get_db_connection() == mock_db_connection

    @patch("dewey.core.architecture.analyze_architecture.DatabaseConnection")
    def test_get_db_connection_creates_new_connection(self, mock_database_connection: MagicMock, analyzer: AnalyzeArchitecture) -> None:
        """Test that _get_db_connection creates a new connection if one isn't provided."""
        analyzer._db_connection = None
        analyzer.config = {"db": "test_db"}
        mock_database_connection.return_value = "new_db_connection"
        assert analyzer._get_db_connection() == "new_db_connection"
        mock_database_connection.assert_called_with(analyzer.config)

    def test_get_llm_client_uses_provided_client(self, analyzer: AnalyzeArchitecture, mock_llm_client: MockLLMClient) -> None:
        """Test that _get_llm_client returns the provided client if available."""
        assert analyzer._get_llm_client() == mock_llm_client

    def test_get_llm_client_uses_self_llm_client(self, analyzer: AnalyzeArchitecture, mock_llm_client: MockLLMClient) -> None:
        """Test that _get_llm_client returns self.llm_client if one isn't provided."""
        analyzer._llm_client = None
        analyzer.llm_client = "self_llm_client"
        assert analyzer._get_llm_client() == "self_llm_client"

    def test_run_success(self, analyzer: AnalyzeArchitecture, mock_db_connection: MockDatabaseConnection, mock_llm_client: MockLLMClient) -> None:
        """Test the run method of the AnalyzeArchitecture class with successful database and LLM calls."""
        analyzer.get_config_value = MagicMock(return_value="test_value")
        analyzer.logger.info = MagicMock()
        mock_db_connection.execute = MagicMock()

        analyzer.run()

        analyzer.logger.info.assert_any_call("Starting architecture analysis...")
        analyzer.get_config_value.assert_called_with("utils.example_config")
        mock_db_connection.execute.assert_called_with("SELECT 1;")
        analyzer.logger.info.assert_any_call("Database connection test successful.")
        analyzer.logger.info.assert_any_call("LLM response: Mock LLM Response")
        analyzer.logger.info.assert_any_call("Architecture analysis completed.")

    def test_run_db_failure(self, analyzer: AnalyzeArchitecture, mock_db_connection: MockDatabaseConnection) -> None:
        """Test the run method of the AnalyzeArchitecture class with a failed database connection."""
        analyzer.get_config_value = MagicMock(return_value="test_value")
        analyzer.logger.info = MagicMock()
        mock_db_connection.execute = MagicMock(side_effect=Exception("Database connection failed"))

        analyzer.run()

        analyzer.logger.info.assert_any_call("Starting architecture analysis...")
        analyzer.get_config_value.assert_called_with("utils.example_config")
        analyzer.logger.error.assert_called_with("Database connection test failed: Database connection failed")
        analyzer.logger.info.assert_any_call("Architecture analysis completed.")

    def test_run_llm_failure(self, analyzer: AnalyzeArchitecture, mock_db_connection: MockDatabaseConnection, mock_llm_client: MockLLMClient) -> None:
        """Test the run method of the AnalyzeArchitecture class with a failed LLM call."""
        analyzer.get_config_value = MagicMock(return_value="test_value")
        analyzer.logger.info = MagicMock()
        mock_llm_client.generate_text = MagicMock(side_effect=Exception("LLM call failed"))
        mock_db_connection.execute = MagicMock()

        analyzer.run()

        analyzer.logger.info.assert_any_call("Starting architecture analysis...")
        analyzer.get_config_value.assert_called_with("utils.example_config")
        mock_db_connection.execute.assert_called_with("SELECT 1;")
        analyzer.logger.info.assert_any_call("Database connection test successful.")
        analyzer.logger.error.assert_called_with("LLM call failed: LLM call failed")
        analyzer.logger.info.assert_any_call("Architecture analysis completed.")

    @patch("dewey.core.architecture.analyze_architecture.AnalyzeArchitecture.execute")
    @patch("dewey.core.architecture.analyze_architecture.AnalyzeArchitecture.__init__", return_value=None)
    def test_main(self, mock_init: MagicMock, mock_execute: MagicMock) -> None:
        """Test the main execution block of the AnalyzeArchitecture class."""
        with patch(
            "dewey.core.architecture.analyze_architecture.AnalyzeArchitecture", autospec=True
        ) as MockAnalyzer:
            # Simulate running the script directly
            import dewey.core.architecture.analyze_architecture

            dewey.core.architecture.analyze_architecture.main()  # type: ignore

            # Assert that AnalyzeArchitecture was instantiated and execute was called
            MockAnalyzer.assert_called_once()
            mock_execute.assert_called_once()
