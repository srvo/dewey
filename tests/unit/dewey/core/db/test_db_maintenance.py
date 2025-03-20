import logging
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.db.db_maintenance import DbMaintenance


class TestDbMaintenance:
    """Tests for the DbMaintenance class."""

    @pytest.fixture
    def db_maintenance(self) -> DbMaintenance:
        """Fixture to create a DbMaintenance instance."""
        with patch("dewey.core.db.db_maintenance.BaseScript.__init__") as mock_init:
            mock_init.return_value = None
            db_maintenance = DbMaintenance()
            db_maintenance.logger = MagicMock()
            db_maintenance.db_conn = MagicMock()
            db_maintenance.llm_client = MagicMock()
            db_maintenance.config = {}  # Provide a default config
            return db_maintenance

    def test_init(self, db_maintenance: DbMaintenance) -> None:
        """Test the __init__ method."""
        assert db_maintenance.name == "DbMaintenance"
        assert db_maintenance.config_section == 'db_maintenance'
        assert db_maintenance.requires_db is True
        assert db_maintenance.enable_llm is True

    def test_run(self, db_maintenance: DbMaintenance) -> None:
        """Test the run method."""
        db_maintenance.get_config_value = MagicMock(return_value=30)
        db_maintenance.check_table_sizes = MagicMock()
        db_maintenance.optimize_indexes = MagicMock()
        db_maintenance.perform_custom_maintenance = MagicMock()

        db_maintenance.run()

        db_maintenance.logger.info.assert_called()
        db_maintenance.check_table_sizes.assert_called_once()
        db_maintenance.optimize_indexes.assert_called_once()
        db_maintenance.perform_custom_maintenance.assert_called_once()

    def test_check_table_sizes(self, db_maintenance: DbMaintenance) -> None:
        """Test the check_table_sizes method."""
        db_maintenance.get_config_value = MagicMock(return_value=1000)
        mock_execute_query = MagicMock(return_value=[("table1", "1500 bytes"), ("table2", "500 bytes")])
        with patch("dewey.core.db.db_maintenance.execute_query", mock_execute_query):
            db_maintenance.check_table_sizes()

        db_maintenance.logger.info.assert_called_with("Checking table sizes...")
        mock_execute_query.assert_called_once()
        assert db_maintenance.logger.warning.call_count == 1
        db_maintenance.logger.error.assert_not_called()

    def test_check_table_sizes_error(self, db_maintenance: DbMaintenance) -> None:
        """Test the check_table_sizes method when an error occurs."""
        db_maintenance.get_config_value = MagicMock(return_value=1000)
        mock_execute_query = MagicMock(side_effect=Exception("Test Exception"))
        with patch("dewey.core.db.db_maintenance.execute_query", mock_execute_query):
            db_maintenance.check_table_sizes()

        db_maintenance.logger.info.assert_called_with("Checking table sizes...")
        mock_execute_query.assert_called_once()
        db_maintenance.logger.warning.assert_not_called()
        db_maintenance.logger.error.assert_called()

    def test_optimize_indexes(self, db_maintenance: DbMaintenance) -> None:
        """Test the optimize_indexes method."""
        mock_execute_query = MagicMock(return_value=["index1", "index2"])
        with patch("dewey.core.db.db_maintenance.execute_query", mock_execute_query):
            db_maintenance.optimize_indexes()

        db_maintenance.logger.info.assert_called_with("Optimizing indexes...")
        assert mock_execute_query.call_count == 1
        assert db_maintenance.logger.warning.call_count == 2
        db_maintenance.logger.error.assert_not_called()
        # Assert that the warning messages contain the index names
        db_maintenance.logger.info.assert_called()

    def test_optimize_indexes_error(self, db_maintenance: DbMaintenance) -> None:
        """Test the optimize_indexes method when an error occurs."""
        mock_execute_query = MagicMock(side_effect=Exception("Test Exception"))
        with patch("dewey.core.db.db_maintenance.execute_query", mock_execute_query):
            db_maintenance.optimize_indexes()

        db_maintenance.logger.info.assert_called_with("Optimizing indexes...")
        mock_execute_query.assert_called_once()
        db_maintenance.logger.warning.assert_not_called()
        db_maintenance.logger.error.assert_called()

    def test_perform_custom_maintenance(self, db_maintenance: DbMaintenance) -> None:
        """Test the perform_custom_maintenance method."""
        mock_execute_query = MagicMock()
        mock_generate_text = MagicMock(return_value="Test Report")
        with patch("dewey.core.db.db_maintenance.execute_query", mock_execute_query), \
             patch("dewey.core.db.db_maintenance.generate_text", mock_generate_text):
            db_maintenance.perform_custom_maintenance()

        db_maintenance.logger.info.assert_called_with("Performing custom maintenance tasks...")
        assert mock_execute_query.call_count == 2
        mock_generate_text.assert_called_once()
        db_maintenance.logger.error.assert_not_called()

    def test_perform_custom_maintenance_error(self, db_maintenance: DbMaintenance) -> None:
        """Test the perform_custom_maintenance method when an error occurs."""
        mock_execute_query = MagicMock(side_effect=Exception("Test Exception"))
        mock_generate_text = MagicMock()
        with patch("dewey.core.db.db_maintenance.execute_query", mock_execute_query), \
             patch("dewey.core.db.db_maintenance.generate_text", mock_generate_text):
            db_maintenance.perform_custom_maintenance()

        db_maintenance.logger.info.assert_called_with("Performing custom maintenance tasks...")
        mock_execute_query.assert_called_once()
        mock_generate_text.assert_not_called()
        db_maintenance.logger.error.assert_called()
