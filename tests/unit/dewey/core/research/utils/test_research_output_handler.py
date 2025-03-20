import pytest
from unittest.mock import patch, mock_open
from dewey.core.research.utils.research_output_handler import ResearchOutputHandler
from dewey.core.base_script import BaseScript
import logging
from pathlib import Path
from typing import Dict, Any


class TestResearchOutputHandler:
    """Unit tests for the ResearchOutputHandler class."""

    @pytest.fixture
    def research_output_handler(self) -> ResearchOutputHandler:
        """Fixture to create a ResearchOutputHandler instance."""
        with patch.object(BaseScript, '_load_config') as mock_load_config:
            mock_load_config.return_value = {
                "research_data": {"output_path": "test_output.txt"}
            }
            handler = ResearchOutputHandler()
            handler.logger = logging.getLogger(__name__)  # Ensure logger is set
            return handler

    def test_init(self, research_output_handler: ResearchOutputHandler) -> None:
        """Test the initialization of the ResearchOutputHandler."""
        assert research_output_handler.output_path == "test_output.txt"
        assert research_output_handler.requires_db is True

    @patch("dewey.core.research.utils.research_output_handler.open", new_callable=mock_open)
    def test_save_output_file(self, mock_file: mock_open, research_output_handler: ResearchOutputHandler) -> None:
        """Test saving output to a file."""
        output_data: Dict[str, Any] = {"key1": "value1", "key2": "value2"}
        research_output_handler.save_output(output_data)
        mock_file.assert_called_once_with(research_output_handler.output_path, "w")
        mock_file().write.assert_called_once_with(str(output_data))
        # Check log message
        assert "Research output saved to: test_output.txt" in research_output_handler.logger.handlers[0].format(
            research_output_handler.logger.handlers[0].record_factory(
                "INFO", 10, "", 0, "", (), None
            )
        )

    @patch("dewey.core.research.utils.research_output_handler.open", side_effect=Exception("File error"))
    def test_save_output_file_error(self, mock_file: mock_open, research_output_handler: ResearchOutputHandler) -> None:
        """Test handling an error when saving output to a file."""
        output_data: Dict[str, Any] = {"key1": "value1", "key2": "value2"}
        with pytest.raises(Exception, match="File error"):
            research_output_handler.save_output(output_data)
        # Check log message
        assert "Error saving research output: File error" in research_output_handler.logger.handlers[0].format(
            research_output_handler.logger.handlers[0].record_factory(
                "ERROR", 40, "", 0, "", (), None
            )
        )

    def test_save_output_db_no_connection(self, research_output_handler: ResearchOutputHandler) -> None:
        """Test saving output to a database when no connection is available."""
        research_output_handler.db_conn = None
        output_data: Dict[str, Any] = {"key1": "value1", "key2": "value2"}
        research_output_handler.save_output(output_data)
        # Check log message
        assert "Database connection not available. Skipping database save." in research_output_handler.logger.handlers[0].format(
            research_output_handler.logger.handlers[0].record_factory(
                "WARNING", 30, "", 0, "", (), None
            )
        )

    @patch("dewey.core.research.utils.research_output_handler.open", new_callable=mock_open)
    def test_run_success(self, mock_file: mock_open, research_output_handler: ResearchOutputHandler) -> None:
        """Test the successful execution of the run method."""
        research_output_handler.run()
        # Check log messages
        assert "Starting research output handling..." in research_output_handler.logger.handlers[0].format(
            research_output_handler.logger.handlers[0].record_factory(
                "INFO", 20, "", 0, "", (), None
            )
        )
        assert "Research output handling completed successfully." in research_output_handler.logger.handlers[0].format(
            research_output_handler.logger.handlers[0].record_factory(
                "INFO", 20, "", 0, "", (), None
            )
        )

    @patch("dewey.core.research.utils.research_output_handler.ResearchOutputHandler.save_output", side_effect=Exception("Save error"))
    def test_run_error(self, mock_save_output: mock_open, research_output_handler: ResearchOutputHandler) -> None:
        """Test the run method when an error occurs during output saving."""
        research_output_handler.run()
        # Check log messages
        assert "Starting research output handling..." in research_output_handler.logger.handlers[0].format(
            research_output_handler.logger.handlers[0].record_factory(
                "INFO", 20, "", 0, "", (), None
            )
        )
        assert "An error occurred during research output handling: Save error" in research_output_handler.logger.handlers[0].format(
            research_output_handler.logger.handlers[0].record_factory(
                "ERROR", 40, "", 0, "", (), None
            )
        )

    @patch("dewey.core.research.utils.research_output_handler.open", new_callable=mock_open)
    def test_output_path_from_config(self, mock_file: mock_open) -> None:
        """Test that the output path is loaded from the config."""
        config_data = {"research_data": {"output_path": "custom_output_path.txt"}}
        with patch.object(BaseScript, '_load_config') as mock_load_config:
            mock_load_config.return_value = config_data
            handler = ResearchOutputHandler()
            assert handler.output_path == "custom_output_path.txt"
            output_data: Dict[str, Any] = {"key1": "value1", "key2": "value2"}
            handler.save_output(output_data)
            mock_file.assert_called_once_with("custom_output_path.txt", "w")

    def test_get_config_value(self, research_output_handler: ResearchOutputHandler) -> None:
        """Test the get_config_value method."""
        # Mock the config dictionary
        research_output_handler.config = {
            "section1": {"key1": "value1", "key2": "value2"},
            "section2": {"key3": "value3"}
        }

        # Test retrieving existing values
        assert research_output_handler.get_config_value("section1.key1") == "value1"
        assert research_output_handler.get_config_value("section2.key3") == "value3"

        # Test retrieving a value with a default
        assert research_output_handler.get_config_value("section1.key4", "default_value") == "default_value"

        # Test retrieving a missing value without a default
        assert research_output_handler.get_config_value("section3.key5") is None

        # Test retrieving a missing section
        assert research_output_handler.get_config_value("section3") is None

        # Test retrieving a value from a nested dictionary
        research_output_handler.config = {"nested": {"level1": {"level2": "deep_value"}}}
        assert research_output_handler.get_config_value("nested.level1.level2") == "deep_value"

    def test_get_path_absolute(self, research_output_handler: ResearchOutputHandler) -> None:
        """Test get_path with an absolute path."""
        absolute_path = "/absolute/path/to/file.txt"
        resolved_path = research_output_handler.get_path(absolute_path)
        assert resolved_path == Path(absolute_path)

    def test_get_path_relative(self, research_output_handler: ResearchOutputHandler) -> None:
        """Test get_path with a relative path."""
        relative_path = "relative/path/to/file.txt"
        expected_path = research_output_handler.PROJECT_ROOT / relative_path
        resolved_path = research_output_handler.get_path(relative_path)
        assert resolved_path == expected_path
