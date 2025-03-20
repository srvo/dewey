import logging
from unittest.mock import patch

import pytest

from dewey.core.crm.transcripts import TranscriptsModule


class TestTranscriptsModule:
    """Tests for the TranscriptsModule class."""

    @pytest.fixture
    def transcripts_module(self):
        """Fixture for creating a TranscriptsModule instance."""
        return TranscriptsModule()

    def test_init(self, transcripts_module: TranscriptsModule):
        """Test the __init__ method."""
        assert transcripts_module.name == "TranscriptsModule"
        assert transcripts_module.description == "Manages transcript-related tasks."

    @patch("dewey.core.crm.transcripts.TranscriptsModule.get_config_value")
    def test_run_with_config_value(
        self, mock_get_config_value, transcripts_module: TranscriptsModule, caplog
    ):
        """Test the run method when a config value is found."""
        mock_get_config_value.return_value = "test_value"
        with caplog.at_level(logging.INFO):
            transcripts_module.run()
        assert "Running Transcripts module..." in caplog.text
        assert "Example config value: test_value" in caplog.text
        mock_get_config_value.assert_called_once_with("example_config")

    @patch("dewey.core.crm.transcripts.TranscriptsModule.get_config_value")
    def test_run_without_config_value(
        self, mock_get_config_value, transcripts_module: TranscriptsModule, caplog
    ):
        """Test the run method when a config value is not found."""
        mock_get_config_value.return_value = None
        with caplog.at_level(logging.WARNING):
            transcripts_module.run()
        assert "Running Transcripts module..." in caplog.text
        assert "Example config value not found." in caplog.text
        mock_get_config_value.assert_called_once_with("example_config")

    @patch("dewey.core.base_script.BaseScript.get_config_value")
    def test_get_config_value_exists(
        self, mock_super_get_config_value, transcripts_module: TranscriptsModule
    ):
        """Test get_config_value when the key exists."""
        mock_super_get_config_value.return_value = "config_value"
        value = transcripts_module.get_config_value("test_key")
        assert value == "config_value"
        mock_super_get_config_value.assert_called_once_with("test_key", None)

    @patch("dewey.core.base_script.BaseScript.get_config_value")
    def test_get_config_value_exists_with_default(
        self, mock_super_get_config_value, transcripts_module: TranscriptsModule
    ):
        """Test get_config_value when the key exists and a default is provided."""
        mock_super_get_config_value.return_value = "config_value"
        value = transcripts_module.get_config_value("test_key", "default_value")
        assert value == "config_value"
        mock_super_get_config_value.assert_called_once_with("test_key", "default_value")

    @patch("dewey.core.base_script.BaseScript.get_config_value")
    def test_get_config_value_not_exists(
        self, mock_super_get_config_value, transcripts_module: TranscriptsModule
    ):
        """Test get_config_value when the key does not exist."""
        mock_super_get_config_value.return_value = None
        value = transcripts_module.get_config_value("test_key")
        assert value is None
        mock_super_get_config_value.assert_called_once_with("test_key", None)

    @patch("dewey.core.base_script.BaseScript.get_config_value")
    def test_get_config_value_not_exists_with_default(
        self, mock_super_get_config_value, transcripts_module: TranscriptsModule
    ):
        """Test get_config_value when the key does not exist and a default is provided."""
        mock_super_get_config_value.return_value = "default_value"
        value = transcripts_module.get_config_value("test_key", "default_value")
        assert value == "default_value"
        mock_super_get_config_value.assert_called_once_with("test_key", "default_value")
