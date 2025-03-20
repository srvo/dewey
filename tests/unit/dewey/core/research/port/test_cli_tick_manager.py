import logging
from unittest.mock import patch

import pytest

from dewey.core.research.port.cli_tick_manager import CliTickManager


class TestCliTickManager:
    """Unit tests for the CliTickManager class."""

    @pytest.fixture
    def cli_tick_manager(self):
        """Fixture to create a CliTickManager instance."""
        with patch("dewey.core.research.port.cli_tick_manager.BaseScript.__init__") as mock_init:
            mock_init.return_value = None
            cli_tick_manager = CliTickManager()
            cli_tick_manager.logger = logging.getLogger(__name__)  # Mock logger
            cli_tick_manager.config = {"cli_tick_manager": {"tick_interval": 60}}  # Mock config
            yield cli_tick_manager

    def test_init(self):
        """Test the __init__ method."""
        with patch("dewey.core.research.port.cli_tick_manager.BaseScript.__init__") as mock_init:
            CliTickManager()
            mock_init.assert_called_once_with(config_section="cli_tick_manager")

    def test_run_default_tick_interval(self, cli_tick_manager, caplog):
        """Test the run method with the default tick interval."""
        caplog.set_level(logging.INFO)
        cli_tick_manager.run()
        assert "CLI tick interval: 60" in caplog.text

    def test_run_custom_tick_interval(self):
        """Test the run method with a custom tick interval."""
        with patch("dewey.core.research.port.cli_tick_manager.BaseScript.__init__") as mock_init:
            mock_init.return_value = None
            cli_tick_manager = CliTickManager()
            cli_tick_manager.logger = logging.getLogger(__name__)  # Mock logger
            cli_tick_manager.config = {"cli_tick_manager": {"tick_interval": 120}}  # Mock config
            with patch.object(cli_tick_manager, 'get_config_value', return_value=120):
                with patch("logging.Logger.info") as mock_logger_info:
                    cli_tick_manager.run()
                    mock_logger_info.assert_called_with("CLI tick interval: 120")

    def test_run_no_tick_interval_in_config(self):
        """Test the run method when tick_interval is not in the config."""
        with patch("dewey.core.research.port.cli_tick_manager.BaseScript.__init__") as mock_init:
            mock_init.return_value = None
            cli_tick_manager = CliTickManager()
            cli_tick_manager.logger = logging.getLogger(__name__)  # Mock logger
            cli_tick_manager.config = {"cli_tick_manager": {}}  # Mock config
            with patch.object(cli_tick_manager, 'get_config_value', return_value=None):
                with patch("logging.Logger.info") as mock_logger_info:
                    cli_tick_manager.run()
                    mock_logger_info.assert_called_with("CLI tick interval: None")

    def test_run_exception_handling(self, cli_tick_manager, caplog):
        """Test the run method handles exceptions gracefully."""
        caplog.set_level(logging.ERROR)
        with patch.object(cli_tick_manager, 'get_config_value', side_effect=Exception("Config error")):
            cli_tick_manager.run()
            assert "Config error" not in caplog.text
