import logging
import os
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import yaml

from dewey.core.base_script import BaseScript
from dewey.core.crm.csv_contact_integration import CsvContactIntegration


@pytest.fixture
def mock_base_script(tmp_path: Path) -> MagicMock:
    """Mocks the BaseScript class and its methods."""
    mock=None, return_value=mock_base_script):
        if tmp_path: Path) -> MagicMock:
    """Mocks the BaseScript class and its methods."""
    mock is None:
            tmp_path: Path) -> MagicMock:
    """Mocks the BaseScript class and its methods."""
    mock = MagicMock(spec=BaseScript)
    mock.logger = MagicMock(spec=logging.Logger)
    mock.config = {}
    mock.get_config_value.return_value = str(tmp_path / "default_path.csv")
    return mock


@pytest.fixture
def csv_contact_integration(mock_base_script: MagicMock) -> CsvContactIntegration:
    """Creates an instance of CsvContactIntegration with mocked dependencies."""
    with patch("dewey.core.crm.csv_contact_integration.BaseScript"
        integration = CsvContactIntegration()
    integration.logger = mock_base_script.logger
    integration.config = mock_base_script.config
    integration.get_config_value = mock_base_script.get_config_value
    return integration


@pytest.fixture
def mock_pandas_read_csv(mocker: pytest.FixtureRequest) -> MagicMock:
    """Mocks the pandas.read_csv function."""
    return mocker.patch("pandas.read_csv")


@pytest.fixture
def mock_db_conn(mocker: pytest.FixtureRequest) -> MagicMock:
    """Mocks the database connection object."""
    return mocker.MagicMock()


def test_csv_contact_integration_init(csv_contact_integration: CsvContactIntegration) -> None:
    """Tests the initialization of the CsvContactIntegration class."""
    assert csv_contact_integration.name == "CsvContactIntegration"
    assert csv_contact_integration.description is None
    assert csv_contact_integration.config_section == "csv_contact_integration"
    assert csv_contact_integration.requires_db is True


def test_run_success(
    csv_contact_integration: CsvContactIntegration, tmp_path: Path, mock_pandas_read_csv: MagicMock
) -> None:
    """Tests the successful execution of the run method."""
    file_path = tmp_path / "default_path.csv"
    file_path.write_text("col1,col2\nval1,val2")
    mock_pandas_read_csv.return_value = pd.DataFrame({"col1": ["val1"], "col2": ["val2"]})

    with patch.object(csv_contact_integration, "process_csv") as mock_process_csv:
        csv_contact_integration.run()
        mock_process_csv.assert_called_once_with(str(file_path))
    csv_contact_integration.logger.info.assert_called_with("CSV contact integration completed.")


def test_run_file_not_found(csv_contact_integration: CsvContactIntegration, mock_base_script: MagicMock) -> None:
    """Tests the run method when the specified file is not found."""
    mock_base_script.get_config_value.return_value = "nonexistent_file.csv"

    with pytest.raises(FileNotFoundError):
        csv_contact_integration.run()
    csv_contact_integration.logger.error.assert_called_once()


def test_run_exception(
    csv_contact_integration: CsvContactIntegration, tmp_path: Path, mock_pandas_read_csv: MagicMock
) -> None:
    """Tests the run method when an exception occurs during processing."""
    file_path = tmp_path / "default_path.csv"
    file_path.write_text("col1,col2\nval1,val2")
    mock_pandas_read_csv.return_value = pd.DataFrame({"col1": ["val1"], "col2": ["val2"]})

    with patch.object(csv_contact_integration, "process_csv", side_effect=Exception("Test exception")):
        with pytest.raises(Exception, match="Test exception"):
            csv_contact_integration.run()
        csv_contact_integration.logger.error.assert_called()


def test_process_csv_success(
    csv_contact_integration: CsvContactIntegration, tmp_path: Path, mock_pandas_read_csv: MagicMock
) -> None:
    """Tests the successful execution of the process_csv method."""
    file_path = tmp_path / "test.csv"
    file_path.write_text("col1,col2\nval1,val2")
    df = pd.DataFrame({"col1": ["val1"], "col2": ["val2"]})
    mock_pandas_read_csv.return_value = df

    with patch.object(csv_contact_integration, "insert_contact") as mock_insert_contact:
        csv_contact_integration.process_csv(str(file_path))
        mock_pandas_read_csv.assert_called_once_with(str(file_path))
        mock_insert_contact.assert_called_once_with(df.iloc[0].to_dict())
    csv_contact_integration.logger.info.assert_called_with("CSV processing completed.")


def test_process_csv_exception(
    csv_contact_integration: CsvContactIntegration, tmp_path: Path, mock_pandas_read_csv: MagicMock
) -> None:
    """Tests the process_csv method when an exception occurs during CSV processing."""
    file_path = tmp_path / "test.csv"
    mock_pandas_read_csv.side_effect = Exception("Test exception")

    with pytest.raises(Exception, match="Test exception"):
        csv_contact_integration.process_csv(str(file_path))
    csv_contact_integration.logger.error.assert_called()


def test_insert_contact_success(
    csv_contact_integration: CsvContactIntegration, mock_db_conn: MagicMock
) -> None:
    """Tests the successful execution of the insert_contact method."""
    contact_data: Dict[str, Any] = {"col1": "val1", "col2": "val2"}
    csv_contact_integration.db_conn = mock_db_conn

    csv_contact_integration.insert_contact(contact_data)

    expected_query = "INSERT INTO contacts (col1, col2) VALUES ('val1', 'val2')"
    mock_db_conn.execute.assert_called_once_with(expected_query)
    csv_contact_integration.logger.info.assert_called()


def test_insert_contact_exception(
    csv_contact_integration: CsvContactIntegration, mock_db_conn: MagicMock
) -> None:
    """Tests the insert_contact method when an exception occurs during contact insertion."""
    contact_data: Dict[str, Any] = {"col1": "val1", "col2": "val2"}
    csv_contact_integration.db_conn = mock_db_conn
    mock_db_conn.execute.side_effect = Exception("Test exception")

    with pytest.raises(Exception, match="Test exception"):
        csv_contact_integration.insert_contact(contact_data)
    csv_contact_integration.logger.error.assert_called()


def test_insert_contact_empty_data(
    csv_contact_integration: CsvContactIntegration, mock_db_conn: MagicMock
) -> None:
    """Tests the insert_contact method with empty contact data."""
    contact_data: Dict[str, Any]=None):
  if Any] is None:
      Any] = {}
    csv_contact_integration.db_conn = mock_db_conn

    with pytest.raises(Exception  # Assuming empty data will cause an exception
        csv_contact_integration.insert_contact(contact_data)
    csv_contact_integration.logger.error.assert_called()


def test_insert_contact_invalid_data(
    csv_contact_integration: CsvContactIntegration, mock_db_conn: MagicMock
) -> None:
    """Tests the insert_contact method with invalid contact data (e.g., non-string values)."""
    contact_data: Dict[str, Any] = {"col1": 123, "col2": True}
    csv_contact_integration.db_conn = mock_db_conn

    with pytest.raises(Exception):  # Assuming invalid data will cause an exception
        csv_contact_integration.insert_contact(contact_data)
    csv_contact_integration.logger.error.assert_called()


def test_process_csv_empty_file(
    csv_contact_integration: CsvContactIntegration, tmp_path: Path, mock_pandas_read_csv: MagicMock
) -> None:
    """Tests the process_csv method with an empty CSV file."""
    file_path = tmp_path / "empty.csv"
    file_path.write_text("")
    df = pd.DataFrame()
    mock_pandas_read_csv.return_value = df

    csv_contact_integration.process_csv(str(file_path))

    mock_pandas_read_csv.assert_called_once_with(str(file_path))
    assert not csv_contact_integration.insert_contact.called
    csv_contact_integration.logger.info.assert_called_with("CSV processing completed.")


def test_process_csv_file_with_header_only(
    csv_contact_integration: CsvContactIntegration, tmp_path: Path, mock_pandas_read_csv: MagicMock
) -> None:
    """Tests the process_csv method with a CSV file containing only a header row."""
    file_path = tmp_path / "header_only.csv"
    file_path.write_text("col1,col2")
    df = pd.DataFrame(columns=["col1", "col2"])
    mock_pandas_read_csv.return_value = df

    csv_contact_integration.process_csv(str(file_path))

    mock_pandas_read_csv.assert_called_once_with(str(file_path))
    assert not csv_contact_integration.insert_contact.called
    csv_contact_integration.logger.info.assert_called_with("CSV processing completed.")


def test_process_csv_different_delimiters(
    csv_contact_integration: CsvContactIntegration, tmp_path: Path
) -> None:
    """Tests the process_csv method with different CSV delimiters (e.g., semicolon)."""
    file_path = tmp_path / "semicolon.csv"
    file_path.write_text("col1;col2\nval1;val2")

    with patch("pandas.read_csv", return_value=pd.DataFrame({"col1": ["val1"], "col2": ["val2"]})) as mock_read_csv, \
            patch.object(csv_contact_integration, "insert_contact") as mock_insert_contact:
        csv_contact_integration.process_csv(str(file_path))
        mock_read_csv.assert_called_once_with(str(file_path))
        mock_insert_contact.assert_called_once_with({"col1": "val1", "col2": "val2"})
    csv_contact_integration.logger.info.assert_called_with("CSV processing completed.")


def test_process_csv_missing_values(
    csv_contact_integration: CsvContactIntegration, tmp_path: Path, mock_pandas_read_csv: MagicMock
) -> None:
    """Tests the process_csv method with missing values in the CSV file."""
    file_path = tmp_path / "missing_values.csv"
    file_path.write_text("col1,col2\nval1,\n,val2")
    df = pd.DataFrame({"col1": ["val1", None], "col2": [None, "val2"]})
    mock_pandas_read_csv.return_value = df

    with patch.object(csv_contact_integration, "insert_contact") as mock_insert_contact:
        csv_contact_integration.process_csv(str(file_path))
        calls = [
            pytest.param({"col1": "val1", "col2": None}, id="row1"),
            pytest.param({"col1": None, "col2": "val2"}, id="row2"),
        ]
        mock_insert_contact.assert_called()
    csv_contact_integration.logger.info.assert_called_with("CSV processing completed.")


def test_process_csv_large_file(
    csv_contact_integration: CsvContactIntegration, tmp_path: Path, mock_pandas_read_csv: MagicMock
) -> None:
    """Tests the process_csv method with a large CSV file (e.g., 1000 rows)."""
    file_path = tmp_path / "large.csv"
    num_rows = 1000
    data = {"col1": [f"val1_{i}" for i in range(num_rows)], "col2": [f"val2_{i}" for i in range(num_rows)]}
    df = pd.DataFrame(data)
    df.to_csv(file_path, index=False)
    mock_pandas_read_csv.return_value = df

    with patch.object(csv_contact_integration, "insert_contact") as mock_insert_contact:
        csv_contact_integration.process_csv(str(file_path))
        assert mock_insert_contact.call_count == num_rows
    csv_contact_integration.logger.info.assert_called_with("CSV processing completed.")


def test_process_csv_file_not_found(csv_contact_integration: CsvContactIntegration, tmp_path: Path) -> None:
    """Tests the process_csv method when the specified file is not found."""
    file_path = tmp_path / "nonexistent.csv"

    with pytest.raises(FileNotFoundError):
        csv_contact_integration.process_csv(str(file_path))
    csv_contact_integration.logger.error.assert_called()


def test_process_csv_invalid_csv_format(
    csv_contact_integration: CsvContactIntegration, tmp_path: Path, mock_pandas_read_csv: MagicMock
) -> None:
    """Tests the process_csv method with an invalid CSV format (e.g., missing columns)."""
    file_path = tmp_path / "invalid.csv"
    file_path.write_text("col1\nval1,val2")  # Missing column in the second row
    mock_pandas_read_csv.side_effect = pd.errors.ParserError("Invalid CSV format")

    with pytest.raises(pd.errors.ParserError, match="Invalid CSV format"):
        csv_contact_integration.process_csv(str(file_path))
    csv_contact_integration.logger.error.assert_called()


def test_get_config_value_success(csv_contact_integration: CsvContactIntegration) -> None:
    """Tests the get_config_value method with a valid key."""
    csv_contact_integration.config = {"section": {"key": "value"}}
    value = csv_contact_integration.get_config_value("section.key")
    assert value == "value"


def test_get_config_value_default(csv_contact_integration: CsvContactIntegration) -> None:
    """Tests the get_config_value method with a non-existent key and a default value."""
    csv_contact_integration.config = {"section": {}}
    value = csv_contact_integration.get_config_value("section.nonexistent", "default")
    assert value == "default"


def test_get_config_value_nested_default(csv_contact_integration: CsvContactIntegration) -> None:
    """Tests the get_config_value method with a nested non-existent key and a default value."""
    csv_contact_integration.config = {}
    value = csv_contact_integration.get_config_value("nonexistent.nested", "default")
    assert value == "default"


def test_get_config_value_no_default(csv_contact_integration: CsvContactIntegration) -> None:
    """Tests the get_config_value method with a non-existent key and no default value."""
    csv_contact_integration.config = {"section": {}}
    value = csv_contact_integration.get_config_value("section.nonexistent")
    assert value is None


def test_get_config_value_empty_config(csv_contact_integration: CsvContactIntegration) -> None:
    """Tests the get_config_value method with an empty configuration."""
    csv_contact_integration.config = {}
    value = csv_contact_integration.get_config_value("any.key", "default")
    assert value == "default"


def test_get_config_value_invalid_key(csv_contact_integration: CsvContactIntegration) -> None:
    """Tests the get_config_value method with an invalid key (e.g., empty string)."""
    csv_contact_integration.config = {"section": {"key": "value"}}
    value = csv_contact_integration.get_config_value("", "default")
    assert value == "default"


def test_get_config_value_none_config(csv_contact_integration: CsvContactIntegration) -> None:
    """Tests the get_config_value method when the config attribute is None."""
    csv_contact_integration.config = None  # type: ignore[assignment]
    value = csv_contact_integration.get_config_value("any.key", "default")
    assert value == "default"
