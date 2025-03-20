import logging
from unittest.mock import MagicMock, patch
import pytest
from dewey.core.research.port.tick_report import TickReport


class TestTickReport:
    """Unit tests for the TickReport class."""

    @pytest.fixture
    def tick_report(self) -> TickReport:
        """Fixture to create a TickReport instance with mocked dependencies."""
        with patch("dewey.core.research.port.tick_report.BaseScript.__init__", return_value=None):
            tick_report = TickReport()
            tick_report.logger = MagicMock(spec=logging.Logger)
            tick_report.db_conn = MagicMock()
            tick_report.llm_client = MagicMock()
            tick_report.config = {"api_key": "test_api_key"}
            tick_report.get_config_value = MagicMock(return_value="test_api_key")
            return tick_report

    def test_init(self) -> None:
        """Test the initialization of the TickReport class."""
        with patch("dewey.core.research.port.tick_report.BaseScript.__init__") as mock_init:
            TickReport()
            mock_init.assert_called_once_with(
                config_section="tick_report", requires_db=True, enable_llm=True
            )

    def test_run_success(self, tick_report: TickReport) -> None:
        """Test the run method with successful database and LLM calls."""
        mock_results = ["tick1", "tick2"]
        tick_report.db_conn = MagicMock()
        tick_report.llm_client = MagicMock()
        tick_report.get_config_value = MagicMock(return_value="test_api_key")
        tick_report.db_conn.execute = MagicMock(return_value=mock_results)
        tick_report.llm_client.generate_text = MagicMock(return_value="Test Summary")

        tick_report.run()

        tick_report.logger.info.assert_called()
        tick_report.logger.debug.assert_called_with("API Key: test_api_key")
        tick_report.db_conn.execute.assert_called()
        tick_report.llm_client.generate_text.assert_called()

    def test_run_no_db_connection(self, tick_report: TickReport) -> None:
        """Test the run method when no database connection is available."""
        tick_report.db_conn = None
        tick_report.llm_client = MagicMock()
        tick_report.get_config_value = MagicMock(return_value="test_api_key")
        tick_report.llm_client.generate_text = MagicMock(return_value="Test Summary")

        tick_report.run()

        tick_report.logger.warning.assert_called_with("No database connection available.")
        tick_report.llm_client.generate_text.assert_called()

    def test_run_no_llm_client(self, tick_report: TickReport) -> None:
        """Test the run method when no LLM client is available."""
        tick_report.db_conn = MagicMock()
        tick_report.llm_client = None
        tick_report.get_config_value = MagicMock(return_value="test_api_key")
        mock_results = ["tick1", "tick2"]
        tick_report.db_conn.execute = MagicMock(return_value=mock_results)

        tick_report.run()

        tick_report.logger.warning.assert_called_with("No LLM client available.")
        tick_report.db_conn.execute.assert_called()

    def test_run_exception(self, tick_report: TickReport) -> None:
        """Test the run method when an exception occurs."""
        tick_report.get_config_value = MagicMock(return_value="test_api_key")
        tick_report.db_conn.execute = MagicMock(side_effect=Exception("Test Exception"))

        with pytest.raises(Exception, match="Test Exception"):
            tick_report.run()

        tick_report.logger.error.assert_called()

    def test_get_config_value(self, tick_report: TickReport) -> None:
        """Test the get_config_value method."""
        tick_report.config = {"level1": {"level2": "value"}}
        assert tick_report.get_config_value("level1.level2") == "value"
        assert tick_report.get_config_value("level1.level3", "default") == "default"
        assert tick_report.get_config_value("level4", "default") == "default"
        assert tick_report.get_config_value("level4") is None

