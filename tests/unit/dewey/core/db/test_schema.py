import logging
from unittest.mock import MagicMock, patch

import pytest
from dewey.core.base_script import BaseScript
from dewey.core.db.schema import Schema


class TestSchema:
    """Tests for the Schema class."""

    @pytest.fixture
    def mock_base_script(self) -> MagicMock:
        """Fixture to mock BaseScript."""
        mock = MagicMock(spec=BaseScript)
        mock.logger = MagicMock(spec=logging.Logger)
        mock.config = {"schema": {"db_url": "test_db_url"}}
        mock.get_config_value.return_value = "test_db_url"
        return mock

    @pytest.fixture
    def schema_instance(self, mock_base_script: MagicMock) -> Schema:
        """Fixture to create a Schema instance with a mocked BaseScript."""
        with patch("dewey.core.db.schema.BaseScript.__init__", return_value=None):
            schema = Schema()
            schema.config = mock_base_script.config
            schema.logger = mock_base_script.logger
            schema.get_config_value = mock_base_script.get_config_value
        return schema

    def test_init(self, schema_instance: Schema) -> None:
        """Test the __init__ method of the Schema class."""
        assert schema_instance.config_section == "schema"

    def test_run_success(self, schema_instance: Schema) -> None:
        """Test the run method with successful execution."""
        schema_instance.get_config_value.return_value = "test_db_url"
        schema_instance.run()
        schema_instance.logger.info.assert_called()
        schema_instance.get_config_value.assert_called_with("db_url", "default_db_url")

    def test_run_exception(self, schema_instance: Schema) -> None:
        """Test the run method when an exception is raised."""
        schema_instance.get_config_value.side_effect = Exception("Test exception")
        with pytest.raises(Exception, match="Test exception"):
            schema_instance.run()
        schema_instance.logger.error.assert_called()
