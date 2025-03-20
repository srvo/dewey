import logging
import os
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import ibis
import pandas as pd
import pytest
import yaml

from dewey.core.base_script import BaseScript
from dewey.core.data_upload.upload_csv_files import UploadCsvFiles
from dewey.core.db import utils as db_utils
from dewey.core.db.connection import DatabaseConnection, get_connection
from dewey.llm import llm_utils


class TestUploadCsvFiles:
    """Tests for the UploadCsvFiles class."""

    @pytest.fixture
    def mock_config(self) -> Dict[str, Any]:
        """Mocks the configuration for the UploadCsvFiles class."""
        return {
            "file_path": "test.csv",
            "table_name": "test_table",
            "motherduck_token": "test_token",
        }

    @pytest.fixture
    def mock_base_script(self, mock_config: Dict[str, Any]) -> MagicMock:
        """Mocks the BaseScript class."""
        mock = MagicMock(spec=BaseScript)
        mock.config = mock_config
        mock.get_config_value.side_effect = lambda key, default=None: mock_config.get(
            key, default
        )
        mock.logger = MagicMock()
        return mock

    @pytest.fixture
    def upload_csv_files(
        self, mock_base_script: MagicMock, mock_config: Dict[str, Any]
    ) -> UploadCsvFiles:
        """Creates an instance of UploadCsvFiles with mocked dependencies."""
        with patch(
            "dewey.core.data_upload.upload_csv_files.BaseScript",
            return_value=mock_base_script,
        ):
            uploader = UploadCsvFiles()
            uploader.config = mock_config  # Directly assign the mock config
            uploader.logger = mock_base_script.logger  # Assign the mock logger
            return uploader

    @pytest.fixture
    def mock_dataframe(self) -> pd.DataFrame:
        """Creates a mock Pandas DataFrame."""
        return pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})

    @pytest.fixture
    def mock_ibis_connection(self) -> MagicMock:
        """Creates a mock Ibis connection."""
        con = MagicMock(spec=ibis.backends.base.BaseBackend)
        con.list_tables.return_value = []
        return con

    def test_init(self, upload_csv_files: UploadCsvFiles) -> None:
        """Tests the __init__ method."""
        assert upload_csv_files.config_section == "upload_csv_files"
        assert upload_csv_files.requires_db is True
        assert isinstance(upload_csv_files, UploadCsvFiles)

    @patch("pandas.read_csv")
    @patch("dewey.core.db.utils.create_table_from_dataframe")
    @patch("dewey.core.db.utils.insert_dataframe")
    def test_run_success(
        self,
        mock_insert_dataframe: MagicMock,
        mock_create_table_from_dataframe: MagicMock,
        mock_read_csv: MagicMock,
        upload_csv_files: UploadCsvFiles,
        mock_dataframe: pd.DataFrame,
        mock_ibis_connection: MagicMock,
    ) -> None:
        """Tests the run method with a successful CSV upload."""
        # Arrange
        upload_csv_files.db_conn = mock_ibis_connection
        mock_read_csv.return_value = mock_dataframe
        upload_csv_files.get_config_value = MagicMock(
            side_effect=lambda key, default=None: {
                "file_path": "test.csv",
                "table_name": "test_table",
                "motherduck_token": "test_token",
            }.get(key, default)
        )
        mock_ibis_connection.list_tables.return_value = []

        # Act
        upload_csv_files.run()

        # Assert
        mock_read_csv.assert_called_once_with("test.csv")
        mock_create_table_from_dataframe.assert_called_once_with(
            mock_ibis_connection, "test_table", mock_dataframe
        )
        mock_insert_dataframe.assert_called_once_with(
            mock_ibis_connection, "test_table", mock_dataframe
        )
        upload_csv_files.logger.info.assert_called_with(
            "CSV file upload process completed successfully."
        )

    @patch("pandas.read_csv")
    def test_run_file_not_found(
        self,
        mock_read_csv: MagicMock,
        upload_csv_files: UploadCsvFiles,
        mock_ibis_connection: MagicMock,
    ) -> None:
        """Tests the run method when the specified CSV file does not exist."""
        # Arrange
        upload_csv_files.db_conn = mock_ibis_connection
        mock_read_csv.side_effect = FileNotFoundError("test.csv not found")
        upload_csv_files.get_config_value = MagicMock(
            return_value="test.csv"
        )  # Mock get_config_value

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            upload_csv_files.run()
        upload_csv_files.logger.error.assert_called_once()

    @patch("pandas.read_csv")
    def test_run_table_exists(
        self,
        mock_read_csv: MagicMock,
        upload_csv_files: UploadCsvFiles,
        mock_dataframe: pd.DataFrame,
        mock_ibis_connection: MagicMock,
    ) -> None:
        """Tests the run method when the table already exists in the database."""
        # Arrange
        upload_csv_files.db_conn = mock_ibis_connection
        mock_read_csv.return_value = mock_dataframe
        mock_ibis_connection.list_tables.return_value = ["test_table"]
        upload_csv_files.get_config_value = MagicMock(
            side_effect=lambda key, default=None: {
                "file_path": "test.csv",
                "table_name": "test_table",
                "motherduck_token": "test_token",
            }.get(key, default)
        )

        # Act
        upload_csv_files.run()

        # Assert
        upload_csv_files.logger.info.assert_any_call(
            "Table 'test_table' already exists in the database."
        )
        mock_read_csv.assert_called_once_with("test.csv")

    @patch("pandas.read_csv")
    @patch("dewey.core.db.utils.insert_dataframe")
    def test_run_insert_dataframe_error(
        self,
        mock_insert_dataframe: MagicMock,
        mock_read_csv: MagicMock,
        upload_csv_files: UploadCsvFiles,
        mock_dataframe: pd.DataFrame,
        mock_ibis_connection: MagicMock,
    ) -> None:
        """Tests the run method when there's an error inserting data into the table."""
        # Arrange
        upload_csv_files.db_conn = mock_ibis_connection
        mock_read_csv.return_value = mock_dataframe
        mock_insert_dataframe.side_effect = Exception("Insert error")
        upload_csv_files.get_config_value = MagicMock(
            side_effect=lambda key, default=None: {
                "file_path": "test.csv",
                "table_name": "test_table",
                "motherduck_token": "test_token",
            }.get(key, default)
        )

        # Act & Assert
        with pytest.raises(Exception, match="Insert error"):
            upload_csv_files.run()
        upload_csv_files.logger.error.assert_called_once()

    def test_get_config_value(self, upload_csv_files: UploadCsvFiles) -> None:
        """Tests the get_config_value method."""
        # Arrange
        upload_csv_files.config = {"level1": {"level2": "value"}}

        # Act & Assert
        assert upload_csv_files.get_config_value("level1.level2") == "value"
        assert upload_csv_files.get_config_value("level1.level3", "default") == "default"
        assert upload_csv_files.get_config_value("level3", "default") == "default"

    def test_get_config_value_no_default(self, upload_csv_files: UploadCsvFiles) -> None:
        """Tests the get_config_value method when no default is provided."""
        # Arrange
        upload_csv_files.config = {"level1": {"level2": "value"}}

        # Act & Assert
        assert upload_csv_files.get_config_value("level1.level2") == "value"
        assert upload_csv_files.get_config_value("level1.level3") is None
        assert upload_csv_files.get_config_value("level3") is None

    @patch("pandas.read_csv")
    def test_run_value_error(
        self,
        mock_read_csv: MagicMock,
        upload_csv_files: UploadCsvFiles,
        mock_ibis_connection: MagicMock,
    ) -> None:
        """Tests the run method when the file path is not specified."""
        # Arrange
        upload_csv_files.db_conn = mock_ibis_connection
        mock_read_csv.side_effect = FileNotFoundError("test.csv not found")
        upload_csv_files.get_config_value = MagicMock(
            side_effect=lambda key, default=None: {
                "file_path": None,
                "table_name": "test_table",
                "motherduck_token": "test_token",
            }.get(key, default)
        )

        # Act & Assert
        with pytest.raises(ValueError, match="File path must be specified"):
            upload_csv_files.run()
        upload_csv_files.logger.error.assert_called_once()

    @patch("pandas.read_csv")
    @patch("dewey.core.db.utils.create_table_from_dataframe")
    @patch("dewey.core.db.utils.insert_dataframe")
    def test_run_no_motherduck_token(
        self,
        mock_insert_dataframe: MagicMock,
        mock_create_table_from_dataframe: MagicMock,
        mock_read_csv: MagicMock,
        upload_csv_files: UploadCsvFiles,
        mock_dataframe: pd.DataFrame,
        mock_ibis_connection: MagicMock,
    ) -> None:
        """Tests the run method with a successful CSV upload and no motherduck token."""
        # Arrange
        upload_csv_files.db_conn = mock_ibis_connection
        mock_read_csv.return_value = mock_dataframe
        upload_csv_files.get_config_value = MagicMock(
            side_effect=lambda key, default=None: {
                "file_path": "test.csv",
                "table_name": "test_table",
                "motherduck_token": None,
            }.get(key, default)
        )
        mock_ibis_connection.list_tables.return_value = []

        # Act
        upload_csv_files.run()

        # Assert
        mock_read_csv.assert_called_once_with("test.csv")
        mock_create_table_from_dataframe.assert_called_once_with(
            mock_ibis_connection, "test_table", mock_dataframe
        )
        mock_insert_dataframe.assert_called_once_with(
            mock_ibis_connection, "test_table", mock_dataframe
        )
        upload_csv_files.logger.info.assert_called_with(
            "CSV file upload process completed successfully."
        )
