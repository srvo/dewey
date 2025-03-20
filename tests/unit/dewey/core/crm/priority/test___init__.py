import logging
from unittest.mock import patch

import pytest

from dewey.core.crm.priority import PriorityModule


class TestPriorityModule:
    """Unit tests for the PriorityModule class."""

    @pytest.fixture
    def priority_module(self) -> PriorityModule:
        """Fixture to create a PriorityModule instance."""
        return PriorityModule()

    def test_init(self, priority_module: PriorityModule) -> None:
        """Test the __init__ method."""
        assert priority_module.name == "PriorityModule"
        assert priority_module.description == "Priority Module"
        assert priority_module.config_section == "priority"
        assert priority_module.logger is not None

    @patch("dewey.core.crm.priority.PriorityModule.get_config_value")
    @patch("dewey.core.crm.priority.PriorityModule.db_conn")
    def test_run_success(
        self,
        mock_db_conn: object,
        mock_get_config_value: object,
        priority_module: PriorityModule,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test the run method with successful execution."""
        mock_get_config_value.return_value = "test_value"
        mock_db_conn.return_value = True

        with caplog.at_level(logging.INFO):
            priority_module.run()

        assert "Running priority module..." in caplog.text
        assert "Some config value: test_value" in caplog.text
        assert "Database connection is available." in caplog.text
        assert "Priority logic completed." in caplog.text

    @patch("dewey.core.crm.priority.PriorityModule.get_config_value")
    @patch("dewey.core.crm.priority.PriorityModule.db_conn")
    def test_run_no_db_connection(
        self,
        mock_db_conn: object,
        mock_get_config_value: object,
        priority_module: PriorityModule,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test the run method when the database connection is not available."""
        mock_get_config_value.return_value = "test_value"
        mock_db_conn.return_value = None

        with caplog.at_level(logging.WARNING):
            priority_module.run()

        assert "Running priority module..." in caplog.text
        assert "Some config value: test_value" in caplog.text
        assert "Database connection is not available." in caplog.text
        assert "Priority logic completed." in caplog.text

    @patch("dewey.core.crm.priority.PriorityModule.get_config_value")
    def test_run_exception(
        self,
        mock_get_config_value: object,
        priority_module: PriorityModule,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test the run method when an exception occurs."""
        mock_get_config_value.side_effect = Exception("Test exception")

        with (
            pytest.raises(Exception, match="Test exception"),
            caplog.at_level(logging.ERROR),
        ):
            priority_module.run()

        assert "Running priority module..." in caplog.text
        assert "Error in priority module: Test exception" in caplog.text
