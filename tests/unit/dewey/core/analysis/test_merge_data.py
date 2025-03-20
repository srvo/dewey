import logging
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.analysis.merge_data import MergeData
from dewey.core.base_script import BaseScript


class TestMergeData:
    """Unit tests for the MergeData class."""

    @pytest.fixture
    def merge_data(self) -> MergeData:
        """Fixture to create a MergeData instance."""
        with patch.object(BaseScript, "__init__", return_value=None):
            merge_data = MergeData()
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

    def test_run_success(self, merge_data: MergeData) -> None:
        """Test the run method with successful execution."""
        merge_data.get_config_value = MagicMock(return_value="/test/path")
        merge_data.db_conn.cursor = MagicMock()
        merge_data.llm_client = MagicMock()

        with patch(
            "dewey.core.analysis.merge_data.llm_utils.generate_response"
        ) as mock_generate_response:
            mock_generate_response.return_value = "LLM Response"
            merge_data.run()

        merge_data.logger.info.assert_called()
        merge_data.get_config_value.assert_called_with(
            "input_path", "/default/input/path"
        )
        assert merge_data.logger.info.call_count >= 3  # Check at least 3 info calls

    def test_run_no_db(self, merge_data: MergeData) -> None:
        """Test the run method when the database connection is not available."""
        merge_data.db_conn = None
        merge_data.get_config_value = MagicMock(return_value="/test/path")

        with patch(
            "dewey.core.analysis.merge_data.llm_utils.generate_response"
        ) as mock_generate_response:
            mock_generate_response.return_value = "LLM Response"
            merge_data.run()

        merge_data.logger.warning.assert_called_with(
            "Database connection is not available."
        )

    def test_run_no_llm(self, merge_data: MergeData) -> None:
        """Test the run method when the LLM client is not available."""
        merge_data.llm_client = None
        merge_data.get_config_value = MagicMock(return_value="/test/path")

        merge_data.run()

        merge_data.logger.warning.assert_called_with("LLM client is not available.")

    def test_run_llm_error(self, merge_data: MergeData) -> None:
        """Test the run method when an error occurs during the LLM call."""
        merge_data.get_config_value = MagicMock(return_value="/test/path")
        merge_data.db_conn.cursor = MagicMock()

        with patch(
            "dewey.core.analysis.merge_data.llm_utils.generate_response"
        ) as mock_generate_response:
            mock_generate_response.side_effect = Exception("LLM Error")
            merge_data.run()

        merge_data.logger.error.assert_called()

    def test_run_general_error(self, merge_data: MergeData) -> None:
        """Test the run method when a general error occurs."""
        merge_data.get_config_value = MagicMock(side_effect=Exception("Config Error"))

        with pytest.raises(Exception, match="Config Error"):
            merge_data.run()

        merge_data.logger.error.assert_called()
