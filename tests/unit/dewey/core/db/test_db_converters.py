import logging
from unittest.mock import patch

import pytest

from dewey.core.db.db_converters import DbConverters


class TestDbConverters:
    """Test suite for the DbConverters class."""

    @pytest.fixture
    def db_converters(self) -> DbConverters:
        """Fixture to create an instance of DbConverters."""
        return DbConverters()

    def test_init(self, db_converters: DbConverters) -> None:
        """Test the __init__ method of DbConverters."""
        assert db_converters.config_section == "db_converters"
        assert isinstance(db_converters.logger, logging.Logger)

    @patch("dewey.core.db.db_converters.DbConverters.logger")
    def test_run(self, mock_logger: logging.Logger, db_converters: DbConverters) -> None:
        """Test the run method of DbConverters."""
        db_converters.run()
        mock_logger.info.assert_called()
        assert mock_logger.info.call_count == 2
        assert mock_logger.info.call_args_list[0][0][
            :35
        ] == "Starting database conversion process"
        assert mock_logger.info.call_args_list[1][0][
            :33
        ] == "Database conversion process comple"
