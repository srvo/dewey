import logging
from unittest.mock import patch

import pytest

from dewey.core.engines.sec_engine import SecEngine


class TestSecEngine:
    """Test suite for the SecEngine class."""

    @pytest.fixture
    def sec_engine(self):
        """Fixture to create a SecEngine instance."""
        with patch(
            "dewey.core.engines.sec_engine.SecEngine.get_config_value"
        ) as mock_get_config_value:
            mock_get_config_value.return_value = "test_api_key"
            engine = SecEngine()
        return engine

    def test_sec_engine_initialization(self, sec_engine: SecEngine):
        """Test that SecEngine initializes correctly."""
        assert sec_engine.name == "SecEngine"
        assert sec_engine.config_section == "sec_engine"
        assert sec_engine.logger is not None
        assert isinstance(sec_engine.logger, logging.Logger)

    def test_run_method(self, sec_engine: SecEngine):
        """Test the run method of SecEngine."""
        with patch.object(sec_engine.logger, "info") as mock_info:
            sec_engine.run()
            assert mock_info.call_count >= 2  # Ensure at least two info logs are made
            mock_info.assert_any_call("Starting SEC Engine...")
            mock_info.assert_any_call("SEC Engine finished.")

    def test_run_method_api_key_logging(self, sec_engine: SecEngine):
        """Test that the API key is logged in the run method."""
        with patch.object(sec_engine.logger, "info") as mock_info:
            sec_engine.run()
            mock_info.assert_any_call("Starting SEC Engine...")
            mock_info.assert_any_call("SEC Engine finished.")
            mock_info.assert_any_call("API Key: test_api_key")

    def test_get_config_value_called(self, sec_engine: SecEngine):
        """Test that get_config_value is called during run."""
        with patch.object(sec_engine, "get_config_value") as mock_get_config_value:
            mock_get_config_value.return_value = "test_api_key"
            sec_engine.run()
            mock_get_config_value.assert_called_with("api_key")

    def test_run_method_exception_handling(self, sec_engine: SecEngine):
        """Test that exceptions in run are handled gracefully."""
        with patch.object(sec_engine.logger, "error") as mock_error:
            with patch.object(
                sec_engine, "get_config_value", side_effect=Exception("Config Error")
            ):
                sec_engine.run()
                mock_error.assert_called_once()

    def test_config_section_exists(self, sec_engine: SecEngine):
        """Test that the config section exists."""
        assert sec_engine.config_section == "sec_engine"
