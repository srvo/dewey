import logging
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.tui.workers import Workers


class TestWorkers:
    """Unit tests for the Workers class."""

    @pytest.fixture
    def workers(self) -> Workers:
        """Fixture to create a Workers instance."""
        return Workers()

    def test_init(self, workers: Workers) -> None:
        """Test the __init__ method."""
        assert workers.config_section == 'workers'
        assert workers.name == 'Workers'
        assert workers.logger is not None

    @patch("dewey.core.tui.workers.BaseScript.get_config_value")
    @patch("dewey.core.tui.workers.Workers.db_conn")
    @patch("dewey.core.tui.workers.Workers.llm_client")
    def test_run_success(
        self,
        mock_llm_client: MagicMock,
        mock_db_conn: MagicMock,
        mock_get_config_value: MagicMock,
        workers: Workers,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test the run method with successful database and LLM calls."""
        caplog.set_level(logging.INFO)
        mock_get_config_value.return_value = "test_value"
        mock_db_conn.cursor.return_value.__enter__.return_value.fetchone.return_value = (
            1,
        )
        mock_llm_client.generate_content.return_value.text = "Test joke."

        workers.run()

        assert "Worker started." in caplog.text
        assert "Config value: test_value" in caplog.text
        assert "Database query result: (1,)" in caplog.text
        assert "LLM response: Test joke." in caplog.text

    @patch("dewey.core.tui.workers.BaseScript.get_config_value")
    @patch("dewey.core.tui.workers.Workers.db_conn")
    @patch("dewey.core.tui.workers.Workers.llm_client")
    def test_run_db_error(
        self,
        mock_llm_client: MagicMock,
        mock_db_conn: MagicMock,
        mock_get_config_value: MagicMock,
        workers: Workers,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test the run method with a database error."""
        caplog.set_level(logging.ERROR)
        mock_get_config_value.return_value = "test_value"
        mock_db_conn.cursor.side_effect = Exception("Database error")

        workers.run()

        assert "Error executing database query: Database error" in caplog.text

    @patch("dewey.core.tui.workers.BaseScript.get_config_value")
    @patch("dewey.core.tui.workers.Workers.db_conn")
    @patch("dewey.core.tui.workers.Workers.llm_client")
    def test_run_llm_error(
        self,
        mock_llm_client: MagicMock,
        mock_db_conn: MagicMock,
        mock_get_config_value: MagicMock,
        workers: Workers,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test the run method with an LLM error."""
        caplog.set_level(logging.ERROR)
        mock_get_config_value.return_value = "test_value"
        mock_db_conn.cursor.return_value.__enter__.return_value.fetchone.return_value = (
            1,
        )
        mock_llm_client.generate_content.side_effect = Exception("LLM error")

        workers.run()

        assert "Error calling LLM: LLM error" in caplog.text

    @patch("dewey.core.tui.workers.BaseScript.get_config_value")
    @patch("dewey.core.tui.workers.Workers.db_conn")
    @patch("dewey.core.tui.workers.Workers.llm_client")
    def test_run_general_error(
        self,
        mock_llm_client: MagicMock,
        mock_db_conn: MagicMock,
        mock_get_config_value: MagicMock,
        workers: Workers,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test the run method with a general error."""
        caplog.set_level(logging.ERROR)
        mock_get_config_value.side_effect = Exception("General error")

        with pytest.raises(Exception, match="General error"):
            workers.run()

        assert "Worker failed: General error" in caplog.text

    @patch("dewey.core.tui.workers.BaseScript.get_config_value")
    def test_some_method(
        self, mock_get_config_value: MagicMock, workers: Workers, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test the some_method method."""
        caplog.set_level(logging.DEBUG)
        mock_get_config_value.return_value = 456

        workers.some_method("test_arg")

        assert "Some method called with arg: test_arg" in caplog.text
        assert "Some other config: 456" in caplog.text
