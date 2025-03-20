import logging
import time
from unittest.mock import patch

import pytest

from dewey.core.db.monitor import Monitor


class TestMonitor:
    """Unit tests for the Monitor class."""

    @pytest.fixture
    def mock_base_script(self):
        """Mocks the BaseScript class."""
        with patch("dewey.core.db.monitor.BaseScript.__init__") as mock:
            yield mock

    @pytest.fixture
    def monitor(self, mock_base_script):
        """Fixture for creating a Monitor instance."""
        mock_base_script.return_value = None
        monitor = Monitor()
        return monitor

    def test_monitor_initialization(self, mock_base_script):
        """Tests the initialization of the Monitor class."""
        monitor = Monitor()
        mock_base_script.assert_called_once_with(config_section="monitor")
        assert monitor.interval == 60

    def test_monitor_initialization_with_config(self, monitor):
        """Tests the initialization of the Monitor class with a config value."""
        with patch.object(monitor, "get_config_value", return_value=120):
            monitor = Monitor()
            assert monitor.interval == 120

    @patch("time.sleep")
    @patch.object(Monitor, "monitor_database")
    def test_run(self, mock_monitor_database, mock_sleep, monitor, caplog):
        """Tests the run method of the Monitor class."""
        caplog.set_level(logging.INFO)
        mock_monitor_database.side_effect = [None, Exception("Test Exception")]
        mock_sleep.return_value = None

        with patch.object(monitor, "interval", 0.1):
            with patch.object(monitor, "run") as mock_run:
                mock_run.side_effect = KeyboardInterrupt
                try:
                    monitor.run()
                except KeyboardInterrupt:
                    pass

        assert "Starting database monitor..." in caplog.text
        assert "Monitoring database..." in caplog.text
        assert "An error occurred: Test Exception" in caplog.text
        assert mock_monitor_database.call_count == 2
        assert mock_sleep.call_count == 2

    def test_monitor_database(self, monitor, caplog):
        """Tests the monitor_database method of the Monitor class."""
        caplog.set_level(logging.INFO)
        monitor.monitor_database()
        assert "Monitoring database..." in caplog.text
        # Add assertions to verify database monitoring logic

    def test_get_config_value(self, monitor):
        """Tests the get_config_value method."""
        with patch.object(monitor, "config", {"interval": 30}):
            interval = monitor.get_config_value("interval")
            assert interval == 30

        interval_default = monitor.get_config_value("non_existent_key", 10)
        assert interval_default == 10

    @patch("time.sleep")
    @patch.object(Monitor, "monitor_database")
    def test_run_keyboard_interrupt(
        self, mock_monitor_database, mock_sleep, monitor, caplog
    ):
        """Tests the run method handles KeyboardInterrupt."""
        caplog.set_level(logging.WARNING)
        mock_monitor_database.return_value = None
        mock_sleep.return_value = None

        with patch.object(monitor, "interval", 0.1):
            with patch.object(monitor, "run") as mock_run:
                mock_run.side_effect = KeyboardInterrupt
                try:
                    monitor.run()
                except KeyboardInterrupt:
                    pass

        assert (
            "Script interrupted by user" not in caplog.text
        )  # Because it's handled in execute()

    @patch("time.sleep")
    @patch.object(Monitor, "monitor_database")
    def test_run_exception(self, mock_monitor_database, mock_sleep, monitor, caplog):
        """Tests the run method handles exceptions."""
        caplog.set_level(logging.ERROR)
        mock_monitor_database.side_effect = Exception("Test Exception")
        mock_sleep.return_value = None

        with patch.object(monitor, "interval", 0.1):
            with patch.object(monitor, "run") as mock_run:
                mock_run.side_effect = KeyboardInterrupt
                try:
                    monitor.run()
                except KeyboardInterrupt:
                    pass

        assert "An error occurred: Test Exception" in caplog.text
        assert mock_sleep.call_count == 1
