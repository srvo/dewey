import logging
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.base_script import BaseScript
from dewey.core.db.migrations.consolidate_email_tables import (
    ConsolidateEmailTables,
)


class TestConsolidateEmailTables:
    """Tests for the ConsolidateEmailTables class."""

    @pytest.fixture
    def consolidate_email_tables(self) -> ConsolidateEmailTables:
        """Fixture to create an instance of ConsolidateEmailTables."""
        with patch.object(BaseScript, '__init__', return_value=None):
            consolidate_email_tables = ConsolidateEmailTables()
            consolidate_email_tables.logger = MagicMock()
            consolidate_email_tables.config = {}
            consolidate_email_tables.db_conn = MagicMock()
            consolidate_email_tables.llm_client = MagicMock()
            yield consolidate_email_tables

    def test_init(self) -> None:
        """Test the __init__ method."""
        with patch.object(BaseScript, '__init__') as mock_init:
            consolidate_email_tables = ConsolidateEmailTables()
            mock_init.assert_called_once_with(
                config_section='consolidate_email_tables',
                requires_db=True,
                enable_llm=True,
            )

    def test_run_success(self, consolidate_email_tables: ConsolidateEmailTables) -> None:
        """Test the run method with a successful database connection."""
        consolidate_email_tables.get_config_value = MagicMock(return_value='test_value')
        consolidate_email_tables.run()

        consolidate_email_tables.logger.info.assert_called_with(
            "Email table consolidation completed."
        )
        consolidate_email_tables.logger.debug.assert_called_with(
            "Using some_config_value: test_value"
        )

    def test_run_no_db_connection(self, consolidate_email_tables: ConsolidateEmailTables) -> None:
        """Test the run method when the database connection is not available."""
        consolidate_email_tables.db_conn = None
        consolidate_email_tables.run()
        consolidate_email_tables.logger.error.assert_called_with(
            "Database connection is not available."
        )

    def test_run_exception(self, consolidate_email_tables: ConsolidateEmailTables) -> None:
        """Test the run method when an exception occurs."""
        consolidate_email_tables.get_config_value = MagicMock(
            side_effect=Exception("Test exception")
        )
        with pytest.raises(Exception, match="Test exception"):
            consolidate_email_tables.run()
        consolidate_email_tables.logger.error.assert_called_once()

    @patch("dewey.core.db.migrations.consolidate_email_tables.ConsolidateEmailTables.execute")
    def test_main(self, mock_execute: MagicMock) -> None:
        """Test the main execution block."""
        with patch("dewey.core.db.migrations.consolidate_email_tables.ConsolidateEmailTables") as MockConsolidateEmailTables:
            instance = MockConsolidateEmailTables.return_value
            instance.execute = MagicMock()
import dewey.core.db.migrations.consolidate_email_tables
            dewey.core.db.migrations.consolidate_email_tables.main()
            MockConsolidateEmailTables.assert_called_once()
            instance.execute.assert_called_once()
