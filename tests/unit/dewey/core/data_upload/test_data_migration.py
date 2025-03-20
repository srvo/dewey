import logging
from unittest.mock import patch
from typing import Any
import pytest

from dewey.core.data_upload.data_migration import DataMigration
from dewey.core.base_script import BaseScript


class TestDataMigration:
    """Test suite for the DataMigration class."""

    @pytest.fixture
    def data_migration(self) -> DataMigration:
        """Fixture to create a DataMigration instance."""
        return DataMigration()

    def test_data_migration_initialization(self, data_migration: DataMigration) -> None:
        """Test that DataMigration initializes correctly."""
        assert isinstance(data_migration, DataMigration)
        assert isinstance(data_migration, BaseScript)
        assert data_migration.config_section == "data_migration"

    @patch("dewey.core.data_upload.data_migration.DataMigration._read_data")
    @patch("dewey.core.data_upload.data_migration.DataMigration._transform_data")
    @patch("dewey.core.data_upload.data_migration.DataMigration._write_data")
    def test_run(
        self,
        mock_write_data: Any,
        mock_transform_data: Any,
        mock_read_data: Any,
        data_migration: DataMigration,
    ) -> None:
        """Test the run method orchestrates the data migration process."""
        mock_read_data.return_value = {"data": "source"}
        mock_transform_data.return_value = {"data": "transformed"}

        data_migration.run()

        mock_read_data.assert_called_once()
        mock_transform_data.assert_called_once_with({"data": "source"})
        mock_write_data.assert_called_once_with({"data": "transformed"})

    @patch("dewey.core.data_upload.data_migration.DataMigration.get_config_value")
    def test_read_data(self, mock_get_config_value: Any, data_migration: DataMigration, caplog: pytest.LogCaptureFixture) -> None:
        """Test the _read_data method reads data from the source."""
        mock_get_config_value.return_value = "test_source"
        with caplog.records_property() as records:
            data = data_migration._read_data()
            assert len(records) == 1
            assert records[0].levelname == "INFO"
            assert "Reading data from source type: test_source" in records[0].message
        mock_get_config_value.assert_called_once_with("source_type", "default_source")
        assert data == {"message": "Sample data from source"}

    @patch("dewey.core.data_upload.data_migration.DataMigration.get_config_value")
    def test_transform_data(self, mock_get_config_value: Any, data_migration: DataMigration, caplog: pytest.LogCaptureFixture) -> None:
        """Test the _transform_data method transforms the data."""
        mock_get_config_value.return_value = "test_transformation"
        test_data = {"key": "value"}
        with caplog.records_property() as records:
            transformed_data = data_migration._transform_data(test_data)
            assert len(records) == 1
            assert records[0].levelname == "INFO"
            assert "Transforming data using: test_transformation" in records[0].message
        mock_get_config_value.assert_called_once_with("transformation_type", "default_transformation")
        assert transformed_data == test_data

    @patch("dewey.core.data_upload.data_migration.DataMigration.get_config_value")
    def test_write_data(self, mock_get_config_value: Any, data_migration: DataMigration, caplog: pytest.LogCaptureFixture) -> None:
        """Test the _write_data method writes the data to the destination."""
        mock_get_config_value.return_value = "test_destination"
        test_data = {"key": "value"}
        with caplog.records_property() as records:
            data_migration._write_data(test_data)
            assert len(records) == 2
            assert records[0].levelname == "INFO"
            assert "Writing data to destination type: test_destination" in records[0].message
            assert records[1].levelname == "INFO"
            assert f"Data written: {test_data}" in records[1].message
        mock_get_config_value.assert_called_once_with("destination_type", "default_destination")

    @patch("dewey.core.data_upload.data_migration.DataMigration.get_config_value")
    def test_read_data_config_error(self, mock_get_config_value: Any, data_migration: DataMigration, caplog: pytest.LogCaptureFixture) -> None:
        """Test the _read_data method handles configuration errors."""
        mock_get_config_value.side_effect = Exception("Config error")
        with caplog.records_property() as records:
            data = data_migration._read_data()
            assert len(records) == 0
        mock_get_config_value.assert_called_once_with("source_type", "default_source")
        assert data == {"message": "Sample data from source"}

    @patch("dewey.core.data_upload.data_migration.DataMigration.get_config_value")
    def test_transform_data_config_error(self, mock_get_config_value: Any, data_migration: DataMigration, caplog: pytest.LogCaptureFixture) -> None:
        """Test the _transform_data method handles configuration errors."""
        mock_get_config_value.side_effect = Exception("Config error")
        test_data = {"key": "value"}
        with caplog.records_property() as records:
            transformed_data = data_migration._transform_data(test_data)
            assert len(records) == 0
        mock_get_config_value.assert_called_once_with("transformation_type", "default_transformation")
        assert transformed_data == test_data

    @patch("dewey.core.data_upload.data_migration.DataMigration.get_config_value")
    def test_write_data_config_error(self, mock_get_config_value: Any, data_migration: DataMigration, caplog: pytest.LogCaptureFixture) -> None:
        """Test the _write_data method handles configuration errors."""
        mock_get_config_value.side_effect = Exception("Config error")
        test_data = {"key": "value"}
        with caplog.records_property() as records:
            data_migration._write_data(test_data)
            assert len(records) == 1
            assert records[0].levelname == "INFO"
            assert f"Data written: {test_data}" in records[0].message
        mock_get_config_value.assert_called_once_with("destination_type", "default_destination")

    def test_execute_method(self, data_migration: DataMigration, caplog: pytest.LogCaptureFixture) -> None:
        """Test the execute method."""
        with patch.object(DataMigration, 'parse_args') as mock_parse_args, \
                patch.object(DataMigration, 'run') as mock_run:
            mock_parse_args.return_value = None
            data_migration.execute()
            assert "Starting execution of DataMigration" in caplog.text
            assert "Completed execution of DataMigration" in caplog.text
            mock_run.assert_called_once()

    def test_execute_keyboard_interrupt(self, data_migration: DataMigration, caplog: pytest.LogCaptureFixture) -> None:
        """Test the execute method handles KeyboardInterrupt."""
        with patch.object(DataMigration, 'parse_args') as mock_parse_args, \
                patch.object(DataMigration, 'run') as mock_run:
            mock_parse_args.return_value = None
            mock_run.side_effect = KeyboardInterrupt
            data_migration.execute()
            assert "Script interrupted by user" in caplog.text

    def test_execute_exception(self, data_migration: DataMigration, caplog: pytest.LogCaptureFixture) -> None:
        """Test the execute method handles exceptions."""
        with patch.object(DataMigration, 'parse_args') as mock_parse_args, \
                patch.object(DataMigration, 'run') as mock_run:
            mock_parse_args.return_value = None
            mock_run.side_effect = ValueError("Test exception")
            data_migration.execute()
            assert "Error executing script: Test exception" in caplog.text

    def test_cleanup_method(self, data_migration: DataMigration, caplog: pytest.LogCaptureFixture) -> None:
        """Test the _cleanup method."""
        data_migration.db_conn = MockDBConnection()
        data_migration._cleanup()
        assert "Closing database connection" in caplog.text
        assert data_migration.db_conn.closed

    def test_cleanup_no_db_conn(self, data_migration: DataMigration, caplog: pytest.LogCaptureFixture) -> None:
        """Test the _cleanup method when db_conn is None."""
        data_migration._cleanup()
        assert "Closing database connection" not in caplog.text

    def test_cleanup_exception(self, data_migration: DataMigration, caplog: pytest.LogCaptureFixture) -> None:
        """Test the _cleanup method handles exceptions."""
        data_migration.db_conn = MockDBConnection(raise_exception=True)
        data_migration._cleanup()
        assert "Error closing database connection" in caplog.text

    @patch("os.path.isabs")
    def test_get_path_absolute(self, mock_isabs: Any, data_migration: DataMigration) -> None:
        """Test the get_path method with an absolute path."""
        mock_isabs.return_value = True
        path = "/absolute/path"
        result = data_migration.get_path(path)
        assert str(result) == path

    @patch("os.path.isabs")
    def test_get_path_relative(self, mock_isabs: Any, data_migration: DataMigration) -> None:
        """Test the get_path method with a relative path."""
        mock_isabs.return_value = False
        path = "relative/path"
        expected_path = data_migration.PROJECT_ROOT / path
        result = data_migration.get_path(path)
        assert result == expected_path

    @patch("dewey.core.data_upload.data_migration.DataMigration._load_config")
    def test_get_config_value(self, mock_load_config: Any, data_migration: DataMigration) -> None:
        """Test the get_config_value method."""
        mock_load_config.return_value = {"llm": {"model": "test_model"}}
        value = data_migration.get_config_value("llm.model")
        assert value == "test_model"

    @patch("dewey.core.data_upload.data_migration.DataMigration._load_config")
    def test_get_config_value_default(self, mock_load_config: Any, data_migration: DataMigration) -> None:
        """Test the get_config_value method with a default value."""
        mock_load_config.return_value = {"llm": {"model": "test_model"}}
        value = data_migration.get_config_value("llm.temperature", 0.7)
        assert value == 0.7

    @patch("dewey.core.data_upload.data_migration.DataMigration._load_config")
    def test_get_config_value_nested(self, mock_load_config: Any, data_migration: DataMigration) -> None:
        """Test the get_config_value method with nested keys."""
        mock_load_config.return_value = {"nested": {"level1": {"level2": "value"}}}
        value = data_migration.get_config_value("nested.level1.level2")
        assert value == "value"

    @patch("dewey.core.data_upload.data_migration.DataMigration._load_config")
    def test_get_config_value_missing(self, mock_load_config: Any, data_migration: DataMigration) -> None:
        """Test the get_config_value method when the key is missing."""
        mock_load_config.return_value = {"llm": {"model": "test_model"}}
        value = data_migration.get_config_value("missing.key", "default_value")
        assert value == "default_value"

    @patch("dewey.core.data_upload.data_migration.BaseScript.setup_argparse")
    def test_setup_argparse(self, mock_setup_argparse: Any, data_migration: DataMigration) -> None:
        """Test the setup_argparse method."""
        parser = data_migration.setup_argparse()
        assert parser is not None
        mock_setup_argparse.assert_not_called()

    @patch("dewey.core.data_upload.data_migration.BaseScript.parse_args")
    def test_parse_args(self, mock_parse_args: Any, data_migration: DataMigration) -> None:
        """Test the parse_args method."""
        data_migration.parse_args()
        mock_parse_args.assert_called_once()

class MockDBConnection:
    """Mock database connection for testing."""

    def __init__(self, raise_exception: bool = False) -> None:
        """Initialize the mock connection."""
        self.closed = False
        self.raise_exception = raise_exception

    def close(self) -> None:
        """Mock close method."""
        if self.raise_exception:
            raise Exception("Mock exception during close")
        self.closed = True
