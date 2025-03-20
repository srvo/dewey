import logging
from unittest.mock import MagicMock, patch

import pytest
import yaml

from dewey.core.base_script import BaseScript
from dewey.core.db.connection import DatabaseConnection
from dewey.core.sync import SyncScript


@pytest.fixture
def mock_config(tmp_path):
    """Fixture to create a mock dewey.yaml config file."""
    config_data = {
        "sync": {
            "source_db": {"type": "sqlite", "connection_string": "source.db"},
            "destination_db": {"type": "sqlite", "connection_string": "dest.db"},
        },
        "core": {"logging": {"level": "INFO", "format": "%(message)s"}},
    }
    config_file = tmp_path / "dewey.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)
    return str(config_file)


@pytest.fixture
def sync_script(mock_config):
    """Fixture to create a SyncScript instance with a mock config."""
    with patch("dewey.core.sync.CONFIG_PATH", mock_config):
        script = SyncScript()
        yield script


@pytest.fixture
def mock_db_connection():
    """Fixture to mock a DatabaseConnection."""
    mock_conn = MagicMock(spec=DatabaseConnection)
    mock_conn.connection.return_value.__enter__.return_value.cursor.return_value.fetchall.return_value = [
        (1, "test1"),
        (2, "test2"),
    ]
    return mock_conn


def test_sync_script_initialization(sync_script):
    """Test SyncScript initializes correctly."""
    assert sync_script.name == "SyncScript"
    assert sync_script.config_section == "sync"
    assert sync_script.requires_db is True
    assert sync_script.enable_llm is False
    assert sync_script.source_db is None
    assert sync_script.destination_db is None
    assert isinstance(sync_script, BaseScript)


def test_connect_to_databases_success(sync_script, mock_db_connection):
    """Test connect_to_databases successfully connects to both databases."""
    with patch("dewey.core.sync.get_connection", return_value=mock_db_connection):
        sync_script.connect_to_databases()
        assert sync_script.source_db == mock_db_connection
        assert sync_script.destination_db == mock_db_connection
        assert mock_db_connection.close.call_count == 0


def test_connect_to_databases_missing_config(
    sync_script, mock_config, tmp_path, caplog
):
    """Test connect_to_databases raises ValueError when config is missing."""
    caplog.set_level(logging.ERROR)
    config_data = {
        "sync": {},
        "core": {"logging": {"level": "INFO", "format": "%(message)s"}},
    }
    config_file = tmp_path / "dewey.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)
    with patch("dewey.core.sync.CONFIG_PATH", str(config_file)):
        with pytest.raises(
            ValueError,
            match="Source and destination database configurations must be specified",
        ):
            sync_script.connect_to_databases()
        assert (
            "Source and destination database configurations must be specified"
            in caplog.text
        )


def test_connect_to_databases_connection_error(
    sync_script, mock_config, tmp_path, caplog
):
    """Test connect_to_databases handles connection errors gracefully."""
    caplog.set_level(logging.ERROR)
    with patch(
        "dewey.core.sync.get_connection", side_effect=Exception("Connection failed")
    ):
        with pytest.raises(Exception, match="Connection failed"):
            sync_script.connect_to_databases()
        assert "Failed to connect to databases: Connection failed" in caplog.text


def test_fetch_data_from_source_success(sync_script, mock_db_connection):
    """Test fetch_data_from_source successfully fetches data."""
    sync_script.source_db = mock_db_connection
    data = sync_script.fetch_data_from_source()
    assert data == [(1, "test1"), (2, "test2")]
    mock_db_connection.connection.return_value.__enter__.return_value.cursor.return_value.execute.assert_called_once_with(
        "SELECT * FROM source_table"
    )


def test_fetch_data_from_source_failure(sync_script, mock_db_connection, caplog):
    """Test fetch_data_from_source handles errors gracefully."""
    caplog.set_level(logging.ERROR)
    sync_script.source_db = mock_db_connection
    mock_db_connection.connection.return_value.__enter__.return_value.cursor.return_value.execute.side_effect = Exception(
        "Query failed"
    )
    with pytest.raises(Exception, match="Query failed"):
        sync_script.fetch_data_from_source()
    assert "Failed to fetch data from source: Query failed" in caplog.text


def test_transform_data_success(sync_script):
    """Test transform_data successfully transforms data."""
    data = [(1, "test1"), (2, "test2")]
    transformed_data = sync_script.transform_data(data)
    assert transformed_data == [
        {"id": 1, "value": "test1test1"},
        {"id": 2, "value": "test2test2"},
    ]


def test_transform_data_failure(sync_script, caplog):
    """Test transform_data handles errors gracefully."""
    caplog.set_level(logging.ERROR)
    data = [(1, "test1"), (2, None)]  # Introduce a None value to cause an error
    with pytest.raises(TypeError):
        sync_script.transform_data(data)
    assert "Data transformation failed" in caplog.text


def test_load_data_into_destination_success(sync_script, mock_db_connection):
    """Test load_data_into_destination successfully loads data."""
    sync_script.destination_db = mock_db_connection
    data = [{"id": 1, "value": "test1"}, {"id": 2, "value": "test2"}]
    sync_script.load_data_into_destination(data)
    mock_db_connection.connection.return_value.__enter__.return_value.cursor.return_value.executemany.assert_called_once_with(
        "INSERT INTO destination_table (id, value) VALUES (%s, %s)",
        [(1, "test1"), (2, "test2")],
    )
    mock_db_connection.connection.return_value.__enter__.return_value.commit.assert_called_once()


def test_load_data_into_destination_failure(sync_script, mock_db_connection, caplog):
    """Test load_data_into_destination handles errors gracefully."""
    caplog.set_level(logging.ERROR)
    sync_script.destination_db = mock_db_connection
    data = [{"id": 1, "value": "test1"}, {"id": 2, "value": "test2"}]
    mock_db_connection.connection.return_value.__enter__.return_value.cursor.return_value.executemany.side_effect = Exception(
        "Insert failed"
    )
    with pytest.raises(Exception, match="Insert failed"):
        sync_script.load_data_into_destination(data)
    assert "Failed to load data into destination: Insert failed" in caplog.text


def test_synchronize_data_success(sync_script, mock_db_connection):
    """Test synchronize_data executes successfully."""
    sync_script.source_db = mock_db_connection
    sync_script.destination_db = mock_db_connection
    with patch.object(
        sync_script, "fetch_data_from_source", return_value=[(1, "test1"), (2, "test2")]
    ):
        with patch.object(
            sync_script,
            "transform_data",
            return_value=[
                {"id": 1, "value": "test1test1"},
                {"id": 2, "value": "test2test2"},
            ],
        ):
            with patch.object(sync_script, "load_data_into_destination") as mock_load:
                sync_script.synchronize_data()
                mock_load.assert_called_once_with(
                    [{"id": 1, "value": "test1test1"}, {"id": 2, "value": "test2test2"}]
                )


def test_synchronize_data_failure(sync_script, mock_db_connection, caplog):
    """Test synchronize_data handles errors gracefully."""
    caplog.set_level(logging.ERROR)
    sync_script.source_db = mock_db_connection
    sync_script.destination_db = mock_db_connection
    with patch.object(
        sync_script, "fetch_data_from_source", side_effect=Exception("Fetch failed")
    ):
        with pytest.raises(Exception, match="Fetch failed"):
            sync_script.synchronize_data()
        assert "Data synchronization failed: Fetch failed" in caplog.text


def test_run_success(sync_script, mock_db_connection):
    """Test run executes the full synchronization process successfully."""
    with patch.object(sync_script, "connect_to_databases") as mock_connect:
        with patch.object(sync_script, "synchronize_data") as mock_sync:
            sync_script.run()
            mock_connect.assert_called_once()
            mock_sync.assert_called_once()


def test_run_failure(sync_script, mock_db_connection, caplog):
    """Test run handles errors during the synchronization process."""
    caplog.set_level(logging.ERROR)
    with patch.object(
        sync_script, "connect_to_databases", side_effect=Exception("Connection error")
    ):
        with pytest.raises(Exception, match="Connection error"):
            sync_script.run()
        assert (
            "An error occurred during synchronization: Connection error" in caplog.text
        )


def test_cli_arguments(sync_script, mock_config, caplog):
    """Test command line arguments override configuration."""
    caplog.set_level(logging.DEBUG)
    with patch(
        "sys.argv", ["script_name", "--log-level", "DEBUG", "--config", mock_config]
    ):
        args = sync_script.parse_args()
        assert args.log_level == "DEBUG"
        assert "Log level set to DEBUG" in caplog.text


def test_get_config_value(sync_script):
    """Test get_config_value retrieves values from the config."""
    value = sync_script.get_config_value("sync.source_db.type")
    assert value == "sqlite"
    default_value = sync_script.get_config_value("nonexistent.key", "default")
    assert default_value == "default"


def test_get_path(sync_script):
    """Test get_path returns the correct path."""
    relative_path = sync_script.get_path("data/test.txt")
    assert str(relative_path) == "/Users/srvo/dewey/data/test.txt"
    absolute_path = sync_script.get_path("/tmp/test.txt")
    assert str(absolute_path) == "/tmp/test.txt"
