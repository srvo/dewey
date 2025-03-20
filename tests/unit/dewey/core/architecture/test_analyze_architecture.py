"""Tests for dewey.core.architecture.analyze_architecture."""

import logging
from unittest.mock import patch, MagicMock
from typing import Dict, List, Any, Optional

import pytest

from dewey.core.base_script import BaseScript
from dewey.core.architecture.analyze_architecture import AnalyzeArchitecture
from dewey.core.db.connection import DatabaseConnection
from dewey.llm.llm_utils import LLMClient


class TestAnalyzeArchitecture:
    """Unit tests for the AnalyzeArchitecture class."""

    @pytest.fixture
    def analyzer(self) -> AnalyzeArchitecture:
        """Fixture to create an instance of AnalyzeArchitecture."""
        with patch("dewey.core.architecture.analyze_architecture.BaseScript.__init__", return_value=None):
            analyzer = AnalyzeArchitecture()
            analyzer.logger = MagicMock()
            analyzer.config = {}
            analyzer.db_conn = MagicMock()
            analyzer.llm_client = MagicMock()
            return analyzer

    def test_init(self, analyzer: AnalyzeArchitecture) -> None:
        """Test the initialization of the AnalyzeArchitecture class."""
        assert analyzer.name == "AnalyzeArchitecture"
        assert analyzer.description is None
        assert analyzer.config_section == "analyze_architecture"
        assert analyzer.requires_db is True
        assert analyzer.enable_llm is True

    @patch("dewey.core.architecture.analyze_architecture.DatabaseConnection")
    def test_run_success(self, mock_db_connection: MagicMock, analyzer: AnalyzeArchitecture) -> None:
        """Test the run method of the AnalyzeArchitecture class with successful database and LLM calls."""
        analyzer.get_config_value = MagicMock(return_value="test_value")
        analyzer.llm_client.generate_text = MagicMock(return_value="LLM response")
        mock_db_conn = MagicMock()
        mock_db_connection.return_value.__enter__.return_value = mock_db_conn
        mock_db_conn.execute.return_value = None

        analyzer.run()

        analyzer.logger.info.assert_any_call("Starting architecture analysis...")
        analyzer.get_config_value.assert_called_with("utils.example_config")
        mock_db_connection.assert_called_once()
        mock_db_conn.execute.assert_called_with("SELECT 1;")
        analyzer.logger.info.assert_any_call("Database connection test successful.")
        analyzer.llm_client.generate_text.assert_called_with("Explain the Dewey system architecture.")
        analyzer.logger.info.assert_any_call("LLM response: LLM response")
        analyzer.logger.info.assert_any_call("Architecture analysis completed.")

    @patch("dewey.core.architecture.analyze_architecture.DatabaseConnection")
    def test_run_db_failure(self, mock_db_connection: MagicMock, analyzer: AnalyzeArchitecture) -> None:
        """Test the run method of the AnalyzeArchitecture class with a failed database connection."""
        analyzer.get_config_value = MagicMock(return_value="test_value")
        mock_db_connection.side_effect = Exception("Database connection failed")

        analyzer.run()

        analyzer.logger.info.assert_any_call("Starting architecture analysis...")
        analyzer.get_config_value.assert_called_with("utils.example_config")
        mock_db_connection.assert_called_once()
        analyzer.logger.error.assert_called_with("Database connection test failed: Database connection failed")
        assert analyzer.llm_client.generate_text.call_count == 0
        analyzer.logger.info.assert_any_call("Architecture analysis completed.")

    def test_run_llm_failure(self, analyzer: AnalyzeArchitecture) -> None:
        """Test the run method of the AnalyzeArchitecture class with a failed LLM call."""
        analyzer.get_config_value = MagicMock(return_value="test_value")
        analyzer.llm_client.generate_text = MagicMock(side_effect=Exception("LLM call failed"))
        analyzer.db_conn.execute = MagicMock()

        analyzer.run()

        analyzer.logger.info.assert_any_call("Starting architecture analysis...")
        analyzer.get_config_value.assert_called_with("utils.example_config")
        analyzer.db_conn.execute.assert_called_with("SELECT 1;")
        analyzer.logger.info.assert_any_call("Database connection test successful.")
        analyzer.llm_client.generate_text.assert_called_with("Explain the Dewey system architecture.")
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
