import logging
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.base_script import BaseScript
from dewey.core.db.init_schema import InitSchema


class TestInitSchema:
    """Tests for the InitSchema class."""

    @pytest.fixture
    def init_schema(self) -> InitSchema:
        """Fixture for creating an InitSchema instance."""
        with patch.object(BaseScript, '_setup_logging'):
            init_schema = InitSchema()
        return init_schema

    @pytest.fixture
    def mock_db_utils(self):
        """Fixture for mocking the db_utils module."""
        with patch('dewey.core.db.init_schema.db_utils') as mock:
            yield mock

    def test_init(self, init_schema: InitSchema) -> None:
        """Test the InitSchema initialization."""
        assert init_schema.name == "InitSchema"
        assert init_schema.config_section == "init_schema"
        assert init_schema.requires_db is True
        assert init_schema.db_conn is not None
        assert isinstance(init_schema.logger, logging.Logger)

    @patch.object(InitSchema, '_create_tables')
    def test_run_success(self, mock_create_tables: MagicMock, init_schema: InitSchema) -> None:
        """Test the run method with successful table creation."""
        init_schema.get_config_value = MagicMock(return_value="test_db_url")
        init_schema.run()
        init_schema.logger.info.assert_called_with("Database schema initialized successfully.")
        mock_create_tables.assert_called_once()

    @patch.object(InitSchema, '_create_tables')
    def test_run_failure(self, mock_create_tables: MagicMock, init_schema: InitSchema) -> None:
        """Test the run method with a failure during table creation."""
        init_schema.get_config_value = MagicMock(return_value="test_db_url")
        mock_create_tables.side_effect = Exception("Table creation failed")
        with pytest.raises(Exception, match="Table creation failed"):
            init_schema.run()
        init_schema.logger.error.assert_called_once()

    def test_create_tables_success(self, init_schema: InitSchema, mock_db_utils: MagicMock) -> None:
        """Test the _create_tables method with successful table creation."""
        init_schema._create_tables()
        init_schema.logger.info.assert_called_with("Tables created successfully.")

    def test_create_tables_failure(self, init_schema: InitSchema, mock_db_utils: MagicMock) -> None:
        """Test the _create_tables method with a failure during table creation."""
        mock_db_utils.create_table.side_effect = Exception("Table creation failed")
        with pytest.raises(Exception, match="Table creation failed"):
            init_schema._create_tables()
        init_schema.logger.error.assert_called_once()

    @patch.object(InitSchema, 'execute')
    def test_main(self, mock_execute: MagicMock) -> None:
        """Test the main execution block."""
        with patch('dewey.core.db.init_schema.InitSchema') as mock_init_schema:
            # Simulate running the script from the command line
            import dewey.core.db.init_schema
            mock_init_schema.return_value.execute.assert_called_once()
