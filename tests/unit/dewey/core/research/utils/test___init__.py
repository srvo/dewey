import logging
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.research.utils import ResearchUtils


class TestResearchUtils:
    """Tests for the ResearchUtils class."""

    @pytest.fixture
    def research_utils(self) -> ResearchUtils:
        """Fixture for creating a ResearchUtils instance."""
        return ResearchUtils()

    def test_init(self, research_utils: ResearchUtils) -> None:
        """Tests the __init__ method."""
        assert research_utils.name == "ResearchUtils"
        assert (
            research_utils.description
            == "Provides utility functions for research workflows."
        )
        assert research_utils.config_section == "research_utils"
        assert not research_utils.requires_db
        assert not research_utils.enable_llm

    @patch("dewey.core.research.utils.ResearchUtils.get_config_value")
    def test_run(
        self,
        mock_get_config_value: MagicMock,
        research_utils: ResearchUtils,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Tests the run method."""
        mock_get_config_value.return_value = "test_value"
        with caplog.record_tuples():
            caplog.set_level(logging.INFO)
            research_utils.run()
        assert (
            "dewey.core.research.utils",
            logging.INFO,
            "Starting ResearchUtils...",
        ) in caplog.record_tuples()
        assert (
            "dewey.core.research.utils",
            logging.INFO,
            "Example config value: test_value",
        ) in caplog.record_tuples()
        assert (
            "dewey.core.research.utils",
            logging.INFO,
            "Executing example utility function...",
        ) in caplog.record_tuples()
        assert (
            "dewey.core.research.utils",
            logging.INFO,
            "Example utility function completed.",
        ) in caplog.record_tuples()
        assert (
            "dewey.core.research.utils",
            logging.INFO,
            "ResearchUtils completed.",
        ) in caplog.record_tuples()
        assert mock_get_config_value.call_count == 1
        assert mock_get_config_value.call_args[0] == ("example_config", "default_value")

    @patch("dewey.core.research.utils.ResearchUtils.logger")
    def test__example_utility_function(
        self, mock_logger: MagicMock, research_utils: ResearchUtils
    ) -> None:
        """Tests the _example_utility_function method."""
        research_utils._example_utility_function()
        assert mock_logger.info.call_count == 2
        mock_logger.info.assert_any_call("Executing example utility function...")
        mock_logger.info.assert_any_call("Example utility function completed.")

    @pytest.mark.parametrize(
        "data_source, config_value, expected_result, log_level, log_message",
        [
            (
                "valid_source",
                "some_data",
                "some_data",
                logging.INFO,
                "Successfully retrieved data from valid_source.",
            ),
            (
                "empty_source",
                None,
                None,
                logging.WARNING,
                "No data found for data source: empty_source.",
            ),
        ],
    )
    @patch("dewey.core.research.utils.ResearchUtils.get_config_value")
    def test_get_data_success(
        self,
        mock_get_config_value: MagicMock,
        research_utils: ResearchUtils,
        data_source: str,
        config_value: Any,
        expected_result: Any,
        log_level: int,
        log_message: str,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Tests the get_data method with successful data retrieval."""
        mock_get_config_value.return_value = config_value
        with caplog.record_tuples():
            caplog.set_level(logging.INFO)
            result = research_utils.get_data(data_source)
        assert result == expected_result
        assert mock_get_config_value.call_args[0] == (data_source,)
        assert (
            "dewey.core.research.utils",
            log_level,
            log_message,
        ) in caplog.record_tuples()

    @patch("dewey.core.research.utils.ResearchUtils.get_config_value")
    def test_get_data_error(
        self,
        mock_get_config_value: MagicMock,
        research_utils: ResearchUtils,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Tests the get_data method with an error during data retrieval."""
        mock_get_config_value.side_effect = Exception("Simulated error")
        with caplog.record_tuples():
            caplog.set_level(logging.ERROR)
            result = research_utils.get_data("error_source")
        assert result is None
        assert mock_get_config_value.call_args[0] == ("error_source",)
        assert (
            "dewey.core.research.utils",
            logging.ERROR,
            "Error retrieving data from error_source: Simulated error",
        ) in caplog.record_tuples()
