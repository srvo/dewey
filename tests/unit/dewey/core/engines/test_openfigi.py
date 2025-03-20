from unittest.mock import patch

import pytest

from dewey.core.engines.openfigi import OpenFigi


class TestOpenFigi:
    """Test suite for the OpenFigi class."""

    @pytest.fixture
    def openfigi(self) -> OpenFigi:
        """Fixture to create an instance of the OpenFigi class."""
        return OpenFigi()

    def test_init(self, openfigi: OpenFigi) -> None:
        """Test the initialization of the OpenFigi class."""
        assert openfigi.name == "OpenFigi"
        assert openfigi.config_section == "openfigi"
        assert openfigi.logger is not None

    @patch("dewey.core.engines.openfigi.OpenFigi.get_config_value")
    @patch("dewey.core.engines.openfigi.OpenFigi.logger")
    def test_run_api_key_loaded(
        self, mock_logger: Any, mock_get_config_value: Any, openfigi: OpenFigi
    ) -> None:
        """Test the run method when the API key is loaded from config."""
        mock_get_config_value.return_value = "test_api_key"
        openfigi.run()
        mock_logger.info.assert_any_call("OpenFigi script started.")
        mock_logger.info.assert_any_call("API Key loaded from config")
        mock_logger.info.assert_any_call("OpenFigi script finished.")

    @patch("dewey.core.engines.openfigi.OpenFigi.get_config_value")
    @patch("dewey.core.engines.openfigi.OpenFigi.logger")
    def test_run_api_key_not_found(
        self, mock_logger: Any, mock_get_config_value: Any, openfigi: OpenFigi
    ) -> None:
        """Test the run method when no API key is found in config."""
        mock_get_config_value.return_value = None
        openfigi.run()
        mock_logger.info.assert_any_call("OpenFigi script started.")
        mock_logger.warning.assert_called_with("No API Key found in config")
        mock_logger.info.assert_any_call("OpenFigi script finished.")

    @patch("dewey.core.engines.openfigi.OpenFigi.execute")
    def test_execute(self, mock_execute: Any, openfigi: OpenFigi) -> None:
        """Test the execute method."""
        openfigi.execute()
        mock_execute.assert_called_once()
