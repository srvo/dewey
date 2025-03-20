"""Tests for dewey.core.analysis.merge_data."""

import logging
from unittest.mock import MagicMock, patch, mock_open
from typing import Dict, List, Any, Optional, Callable

import pytest

from dewey.core.analysis.merge_data import MergeData, LLMClientInterface
from dewey.core.base_script import BaseScript
from dewey.core.db.connection import DatabaseConnection, get_connection
from dewey.llm import llm_utils


class TestMergeData:
    """Unit tests for the MergeData class."""

    @pytest.fixture
    def merge_data(self) -> MergeData:
        """Fixture to create a MergeData instance with mocked dependencies."""
        with patch.object(BaseScript, "__init__", return_value=None):
            merge_data = MergeData()
            merge_data.logger = MagicMock()
            merge_data.config = {}
            merge_data.db_conn = MagicMock()
            merge_data.llm_client = MagicMock()
        return merge_data

    @pytest.fixture
    def mock_llm_generate_response(self) -> MagicMock:
        """Fixture to mock the llm_utils.generate_response function."""
        return MagicMock()

    @pytest.fixture
    def merge_data_with_mock_llm(self, mock_llm_generate_response: MagicMock) -> MergeData:
        """Fixture to create a MergeData instance with a mocked LLM generate response function."""
        with patch.object(BaseScript, "__init__", return_value=None):
            merge_data = MergeData(llm_generate_response=mock_llm_generate_response)
            merge_data.logger = MagicMock()
            merge_data.config = {}
            merge_data.db_conn = MagicMock()
            merge_data.llm_client = MagicMock()
        return merge_data

    def test_init(self) -> None:
        """Test the __init__ method."""
        with patch.object(BaseScript, "__init__", return_value=None):
            merge_data = MergeData()
            assert merge_data.name == "MergeData"
            assert merge_data.config_section == "merge_data"
            assert merge_data.requires_db is True
            assert merge_data.enable_llm is True

    @patch("dewey.core.analysis.merge_data.get_connection")
    def test_execute_database_query_success(self, mock_get_connection: MagicMock, merge_data: MergeData) -> None:
        """Test _execute_database_query method with successful database query."""
        mock_db_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (1,)  # Simulate a database result
        mock_get_connection.return_value = mock_db_conn
        merge_data.db_conn = mock_db_conn

        result = merge_data._execute_database_query()

        assert result == "(1,)"
        merge_data.logger.info.assert_called_with("Database query result: (1,)")
        mock_cursor.execute.assert_called_with("SELECT 1")

    @patch("dewey.core.analysis.merge_data.get_connection")
    def test_execute_database_query_failure(self, mock_get_connection: MagicMock, merge_data: MergeData) -> None:
        """Test _execute_database_query method with a database error."""
        mock_get_connection.side_effect = Exception("Database connection error")
        merge_data.db_conn = MagicMock()

        result = merge_data._execute_database_query()

        assert result is None
        merge_data.logger.error.assert_called()

    def test_call_llm_success(self, merge_data_with_mock_llm: MergeData, mock_llm_generate_response: MagicMock) -> None:
        """Test _call_llm method with successful LLM call."""
        mock_llm_generate_response.return_value = "LLM Summary"
        merge_data_with_mock_llm.llm_client = MagicMock()

        result = merge_data_with_mock_llm._call_llm("Prompt: ", "Test Text")

        assert result == "LLM Summary"
        merge_data_with_mock_llm.logger.info.assert_called_with("LLM response: LLM Summary")
        mock_llm_generate_response.assert_called()

    def test_call_llm_no_response(self, merge_data_with_mock_llm: MergeData, mock_llm_generate_response: MagicMock) -> None:
        """Test _call_llm method when the LLM returns None."""
        mock_llm_generate_response.return_value = None
        merge_data_with_mock_llm.llm_client = MagicMock()

        result = merge_data_with_mock_llm._call_llm("Prompt: ", "Test Text")

        assert result is None
        merge_data_with_mock_llm.logger.warning.assert_called_with("LLM response was None.")
        mock_llm_generate_response.assert_called()

    def test_call_llm_error(self, merge_data_with_mock_llm: MergeData, mock_llm_generate_response: MagicMock) -> None:
        """Test _call_llm method when an error occurs during the LLM call."""
        mock_llm_generate_response.side_effect = Exception("LLM Error")
        merge_data_with_mock_llm.llm_client = MagicMock()

        result = merge_data_with_mock_llm._call_llm("Prompt: ", "Test Text")

        assert result is None
        merge_data_with_mock_llm.logger.error.assert_called()
        mock_llm_generate_response.assert_called()

    @patch("dewey.core.analysis.merge_data.MergeData._execute_database_query")
    @patch("dewey.core.analysis.merge_data.MergeData._call_llm")
    def test_merge_data_success(self, mock_call_llm: MagicMock, mock_execute_db: MagicMock, merge_data: MergeData) -> None:
        """Test merge_data method with successful execution."""
        merge_data.db_conn = MagicMock()
        merge_data.llm_client = MagicMock()
        mock_execute_db.return_value = "DB Result"
        mock_call_llm.return_value = "LLM Result"

        result = merge_data.merge_data("/test/path")

        assert result is True
        merge_data.logger.info.assert_called()
        mock_execute_db.assert_called()
        mock_call_llm.assert_called()

    def test_merge_data_no_db(self, merge_data: MergeData) -> None:
        """Test merge_data method when the database connection is not available."""
        merge_data.db_conn = None
        merge_data.llm_client = MagicMock()

        result = merge_data.merge_data("/test/path")

        assert result is True
        merge_data.logger.warning.assert_called_with(
            "Database connection is not available."
        )

    def test_merge_data_no_llm(self, merge_data: MergeData) -> None:
        """Test merge_data method when the LLM client is not available."""
        merge_data.db_conn = MagicMock()
        merge_data.llm_client = None

        result = merge_data.merge_data("/test/path")

        assert result is True
        merge_data.logger.warning.assert_called_with("LLM client is not available.")

    @patch("dewey.core.analysis.merge_data.MergeData.merge_data")
    def test_run_success(self, mock_merge_data: MagicMock, merge_data: MergeData) -> None:
        """Test the run method with successful execution."""
        merge_data.get_config_value = MagicMock(return_value="/test/path")
        mock_merge_data.return_value = True

        merge_data.run()

        merge_data.logger.info.assert_called()
        merge_data.get_config_value.assert_called_with(
            "input_path", "/default/input/path"
        )
        mock_merge_data.assert_called_with("/test/path")

    def test_run_general_error(self, merge_data: MergeData) -> None:
        """Test the run method when a general error occurs."""
        merge_data.get_config_value = MagicMock(side_effect=Exception("Config Error"))

        with pytest.raises(Exception, match="Config Error"):
            merge_data.run()

        merge_data.logger.error.assert_called()
