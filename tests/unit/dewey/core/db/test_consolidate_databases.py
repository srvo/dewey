import pytest
from unittest.mock import patch, mock_open
from dewey.core.db.consolidate_databases import ConsolidateDatabases
from dewey.core.base_script import BaseScript
from dewey.core.db.connection import DatabaseConnection
from dewey.core.db import utils as db_utils
from dewey.llm import llm_utils
from typing import Any, Dict, Optional
import logging
import yaml
from pathlib import Path


class MockDatabaseConnection:
    """
    Mocks a database connection for testing purposes.
    """

    def __init__(self):
        self.is_connected = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self.is_connected = False

    def execute(self, query):
        """
        Mock execute method.
        """
        pass


@pytest.fixture
def mock_config(tmp_path: Path) -> Dict[str, Any]:
    """
    Creates a mock dewey.yaml config file for testing.

    Args:
        tmp_path: pytest fixture for a temporary directory.

    Returns:
        A dictionary representing the mock configuration.
    """
    config_data = {
        'consolidate_databases': {
            'source_db_url': 'sqlite:///:memory:',
            'target_db_url': 'sqlite:///:memory:',
        },
        'core': {
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                'date_format': '%Y-%m-%d %H:%M:%S'
            }
        }
    }
    config_file = tmp_path / 'dewey.yaml'
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)
    return config_data


@pytest.fixture
def consolidate_databases_instance(mock_config: Dict[str, Any], tmp_path: Path) -> ConsolidateDatabases:
    """
    Creates an instance of ConsolidateDatabases with a mock configuration.

    Args:
        mock_config: A dictionary representing the mock configuration.
        tmp_path: pytest fixture for a temporary directory.

    Returns:
        An instance of ConsolidateDatabases.
    """
    with patch("dewey.core.base_script.CONFIG_PATH", tmp_path / 'dewey.yaml'):
        consolidator = ConsolidateDatabases()
    return consolidator


def test_consolidate_databases_initialization(consolidate_databases_instance: ConsolidateDatabases) -> None:
    """
    Tests the initialization of the ConsolidateDatabases class.

    Args:
        consolidate_databases_instance: An instance of ConsolidateDatabases.
    """
    assert consolidate_databases_instance.config_section == 'consolidate_databases'
    assert consolidate_databases_instance.requires_db is True
    assert consolidate_databases_instance.db_conn is None  # Connection is lazy-loaded


@patch("dewey.core.db.consolidate_databases.get_connection")
def test_consolidate_databases_run_success(mock_get_connection: Any, consolidate_databases_instance: ConsolidateDatabases) -> None:
    """
    Tests the successful execution of the database consolidation process.

    Args:
        mock_get_connection: Mocked get_connection function.
        consolidate_databases_instance: An instance of ConsolidateDatabases.
    """
    mock_source_conn = MockDatabaseConnection()
    mock_target_conn = MockDatabaseConnection()
    mock_get_connection.side_effect = [mock_source_conn, mock_target_conn]

    consolidate_databases_instance.run()

    assert mock_source_conn.is_connected is False
    assert mock_target_conn.is_connected is False


@patch("dewey.core.db.consolidate_databases.get_connection")
def test_consolidate_databases_run_failure(mock_get_connection: Any, consolidate_databases_instance: ConsolidateDatabases) -> None:
    """
    Tests the failure of the database consolidation process due to a connection error.

    Args:
        mock_get_connection: Mocked get_connection function.
        consolidate_databases_instance: An instance of ConsolidateDatabases.
    """
    mock_get_connection.side_effect = Exception("Connection failed")

    with pytest.raises(Exception, match="Connection failed"):
        consolidate_databases_instance.run()


def test_consolidate_databases_run_no_config(consolidate_databases_instance: ConsolidateDatabases, tmp_path: Path) -> None:
    """
    Tests the failure of the database consolidation process due to missing configuration.

    Args:
        consolidate_databases_instance: An instance of ConsolidateDatabases.
        tmp_path: pytest fixture for a temporary directory.
    """
    # Create a new instance with a config that doesn't have the required values
    config_data = {
        'core': {
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                'date_format': '%Y-%m-%d %H:%M:%S'
            }
        }
    }
    config_file = tmp_path / 'dewey.yaml'
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)

    with patch("dewey.core.base_script.CONFIG_PATH", tmp_path / 'dewey.yaml'):
        consolidator = ConsolidateDatabases()
        with pytest.raises(ValueError, match="Source or target database URL not configured."):
            consolidator.run()


@patch("dewey.core.db.consolidate_databases.ConsolidateDatabases.parse_args")
@patch("dewey.core.db.consolidate_databases.ConsolidateDatabases.run")
def test_consolidate_databases_execute_success(mock_run: Any, mock_parse_args: Any, consolidate_databases_instance: ConsolidateDatabases) -> None:
    """
    Tests the successful execution of the execute method.

    Args:
        mock_run: Mocked run method.
        mock_parse_args: Mocked parse_args method.
        consolidate_databases_instance: An instance of ConsolidateDatabases.
    """
    mock_parse_args.return_value = None  # Simulate successful argument parsing
    consolidate_databases_instance.execute()
    assert mock_run.called


@patch("dewey.core.db.consolidate_databases.ConsolidateDatabases.parse_args")
@patch("dewey.core.db.consolidate_databases.ConsolidateDatabases.run")
def test_consolidate_databases_execute_keyboard_interrupt(mock_run: Any, mock_parse_args: Any, consolidate_databases_instance: ConsolidateDatabases, capsys: pytest.CaptureFixture) -> None:
    """
    Tests the handling of KeyboardInterrupt in the execute method.

    Args:
        mock_run: Mocked run method.
        mock_parse_args: Mocked parse_args method.
        consolidate_databases_instance: An instance of ConsolidateDatabases.
        capsys: pytest fixture for capturing stdout and stderr.
    """
    mock_run.side_effect = KeyboardInterrupt
    mock_parse_args.return_value = None
    consolidate_databases_instance.execute()
    captured = capsys.readouterr()
    assert "Script interrupted by user" in captured.out


@patch("dewey.core.db.consolidate_databases.ConsolidateDatabases.parse_args")
@patch("dewey.core.db.consolidate_databases.ConsolidateDatabases.run")
def test_consolidate_databases_execute_exception(mock_run: Any, mock_parse_args: Any, consolidate_databases_instance: ConsolidateDatabases, capsys: pytest.CaptureFixture) -> None:
    """
    Tests the handling of exceptions in the execute method.

    Args:
        mock_run: Mocked run method.
        mock_parse_args: Mocked parse_args method.
        consolidate_databases_instance: An instance of ConsolidateDatabases.
        capsys: pytest fixture for capturing stdout and stderr.
    """
    mock_run.side_effect = ValueError("Simulated error")
    mock_parse_args.return_value = None
    consolidate_databases_instance.execute()
    captured = capsys.readouterr()
    assert "Error executing script: Simulated error" in captured.out


@patch("dewey.core.db.consolidate_databases.get_connection")
def test_consolidate_databases_cleanup(mock_get_connection: Any, consolidate_databases_instance: ConsolidateDatabases) -> None:
    """
    Tests the cleanup method to ensure the database connection is closed.

    Args:
        mock_get_connection: Mocked get_connection function.
        consolidate_databases_instance: An instance of ConsolidateDatabases.
    """
    mock_db_conn = MockDatabaseConnection()
    consolidate_databases_instance.db_conn = mock_db_conn
    consolidate_databases_instance._cleanup()
    assert mock_db_conn.is_connected is False


def test_consolidate_databases_get_config_value(consolidate_databases_instance: ConsolidateDatabases) -> None:
    """
    Tests the get_config_value method to retrieve configuration values.

    Args:
        consolidate_databases_instance: An instance of ConsolidateDatabases.
    """
    value = consolidate_databases_instance.get_config_value('core.logging.level')
    assert value == 'INFO'
    default_value = consolidate_databases_instance.get_config_value('nonexistent.key', 'default')
    assert default_value == 'default'


def test_consolidate_databases_get_path(consolidate_databases_instance: ConsolidateDatabases) -> None:
    """
    Tests the get_path method to retrieve a path relative to the project root.

    Args:
        consolidate_databases_instance: An instance of ConsolidateDatabases.
    """
    relative_path = consolidate_databases_instance.get_path('config/dewey.yaml')
    assert str(relative_path).endswith('config/dewey.yaml')  # Adjust assertion as needed
    absolute_path = consolidate_databases_instance.get_path('/absolute/path')
    assert str(absolute_path) == '/absolute/path'
