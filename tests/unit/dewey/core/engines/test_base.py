import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
import yaml

from dewey.core.base_script import BaseScript


class MockBaseScript(BaseScript):
    """Mock BaseScript class for testing."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Function __init__."""
        super().__init__(*args, **kwargs)

    def run(self) -> None:
        """Mock run method."""
        pass


@pytest.fixture
def mock_config() -> Dict[str, Any]:
    """Fixture for a mock configuration."""
    return {
        "core": {
            "logging": {"level": "DEBUG", "format": "%(message)s"},
            "database": {"connection_string": "test_db"},
        },
        "llm": {"model": "test_llm"},
        "test_section": {"key1": "value1", "key2": "value2"},
    }


@pytest.fixture
def mock_base_script(mock_config: Dict[str, Any], tmp_path: Path) -> MockBaseScript:
    """Fixture for a mock BaseScript instance."""
    # Create a dummy config file
    config_file = tmp_path / "dewey.yaml"
    with open(config_file, "w") as f:
        yaml.dump(mock_config, f)

    # Patch the CONFIG_PATH to point to the dummy config file
    with patch("dewey.core.base_script.CONFIG_PATH", config_file):
        script = MockBaseScript(
            name="TestScript",
            description="A test script",
            config_section="test_section",
            requires_db=True,
            enable_llm=True,
        )
        yield script


def test_base_script_initialization(mock_base_script: MockBaseScript) -> None:
    """Test BaseScript initialization."""
    assert mock_base_script.name == "TestScript"
    assert mock_base_script.description == "A test script"
    assert mock_base_script.config_section == "test_section"
    assert mock_base_script.requires_db is True
    assert mock_base_script.enable_llm is True
    assert mock_base_script.logger is not None
    assert mock_base_script.config == {"key1": "value1", "key2": "value2"}
    assert mock_base_script.db_conn is not None
    assert mock_base_script.llm_client is not None


def test_setup_logging(mock_base_script: MockBaseScript, mock_config: Dict[str, Any], tmp_path: Path) -> None:
    """Test the _setup_logging method."""
    # Create a dummy config file
    config_file = tmp_path / "dewey.yaml"
    with open(config_file, "w") as f:
        yaml.dump(mock_config, f)

    # Patch the CONFIG_PATH to point to the dummy config file
    with patch("dewey.core.base_script.CONFIG_PATH", config_file):
        mock_base_script._setup_logging()
        assert mock_base_script.logger.level == logging.DEBUG


def test_load_config(mock_base_script: MockBaseScript, mock_config: Dict[str, Any], tmp_path: Path) -> None:
    """Test the _load_config method."""
    # Create a dummy config file
    config_file = tmp_path / "dewey.yaml"
    with open(config_file, "w") as f:
        yaml.dump(mock_config, f)

    # Patch the CONFIG_PATH to point to the dummy config file
    with patch("dewey.core.base_script.CONFIG_PATH", config_file):
        config = mock_base_script._load_config()
        assert config == {"key1": "value1", "key2": "value2"}

    # Test loading the entire config
    mock_base_script.config_section = None
    with patch("dewey.core.base_script.CONFIG_PATH", config_file):
        config = mock_base_script._load_config()
        assert config == mock_config

    # Test FileNotFoundError
    with patch("dewey.core.base_script.CONFIG_PATH", "nonexistent_file.yaml"):
        with pytest.raises(FileNotFoundError):
            mock_base_script._load_config()

    # Test yaml.YAMLError
    config_file = tmp_path / "bad_config.yaml"
    with open(config_file, "w") as f:
        f.write("bad: yaml: content")
    with patch("dewey.core.base_script.CONFIG_PATH", config_file):
        with pytest.raises(yaml.YAMLError):
            mock_base_script._load_config()


@patch("dewey.core.base_script.get_connection")
def test_initialize_db_connection(mock_get_connection: MagicMock, mock_base_script: MockBaseScript) -> None:
    """Test the _initialize_db_connection method."""
    mock_base_script._initialize_db_connection()
    mock_get_connection.assert_called_once_with(
        mock_base_script.config.get("core", {}).get("database", {})
    )
    assert mock_base_script.db_conn=None, side_effect=ImportError):
        if {})
    )
    assert mock_base_script.db_conn is None:
            {})
    )
    assert mock_base_script.db_conn = = mock_get_connection.return_value

    # Test ImportError
    with patch("dewey.core.base_script.get_connection"
        with pytest.raises(ImportError):
            mock_base_script._initialize_db_connection()

    # Test Exception
    mock_get_connection.side_effect = Exception("DB Error")
    with pytest.raises(Exception, match="DB Error"):
        mock_base_script._initialize_db_connection()


@patch("dewey.core.base_script.get_llm_client")
def test_initialize_llm_client(mock_get_llm_client: MagicMock, mock_base_script: MockBaseScript) -> None:
    """Test the _initialize_llm_client method."""
    mock_base_script._initialize_llm_client()
    mock_get_llm_client.assert_called_once_with(mock_base_script.config.get("llm", {}))
    assert mock_base_script.llm_client=None, side_effect=ImportError):
        if {}))
    assert mock_base_script.llm_client is None:
            {}))
    assert mock_base_script.llm_client = = mock_get_llm_client.return_value

    # Test ImportError
    with patch("dewey.core.base_script.get_llm_client"
        with pytest.raises(ImportError):
            mock_base_script._initialize_llm_client()

    # Test Exception
    mock_get_llm_client.side_effect = Exception("LLM Error")
    with pytest.raises(Exception, match="LLM Error"):
        mock_base_script._initialize_llm_client()


def test_setup_argparse(mock_base_script: MockBaseScript) -> None:
    """Test the setup_argparse method."""
    parser = mock_base_script.setup_argparse()
    assert isinstance(parser, argparse.ArgumentParser)
    assert parser.description == "A test script"
    assert any(action.dest == "config" for action in parser._actions)
    assert any(action.dest == "log_level" for action in parser._actions)
    assert any(action.dest == "db_connection_string" for action in parser._actions)
    assert any(action.dest == "llm_model" for action in parser._actions)


@patch("argparse.ArgumentParser.parse_args")
def test_parse_args(mock_parse_args: MagicMock, mock_base_script: MockBaseScript, tmp_path: Path) -> None:
    """Test the parse_args method."""
    # Mock command line arguments
    mock_parse_args.return_value = argparse.Namespace(
        log_level="DEBUG",
        config=str(tmp_path / "custom_config.yaml"),
        db_connection_string="custom_db",
        llm_model="custom_llm",
    )

    # Create a custom config file
    custom_config = {"custom_key": "custom_value"}
    with open(tmp_path / "custom_config.yaml", "w") as f:
        yaml.dump(custom_config, f)

    # Patch the get_connection and get_llm_client functions
    with patch("dewey.core.db.connection.get_connection") as mock_get_connection, patch(
        "dewey.llm.llm_utils.get_llm_client"
    ) as mock_get_llm_client:
        args = mock_base_script.parse_args()

        # Assertions
        assert mock_base_script.logger.level == logging.DEBUG
        assert mock_base_script.config == custom_config
        mock_get_connection.assert_called_once_with({"connection_string": "custom_db"})
        mock_get_llm_client.assert_called_once_with({"model": "custom_llm"})
        assert mock_base_script.db_conn == mock_get_connection.return_value
        assert mock_base_script.llm_client == mock_get_llm_client.return_value
        assert args == mock_parse_args.return_value

    # Test with missing config file
    mock_parse_args.return_value.config = "nonexistent_config.yaml"
    with pytest.raises(SystemExit) as exc_info:
        mock_base_script.parse_args()
    assert exc_info.value.code == 1


def test_run(mock_base_script: MockBaseScript) -> None:
    """Test the abstract run method."""
    with pytest.raises(NotImplementedError):
        mock_base_script.run()


@patch("dewey.core.base_script.MockBaseScript.parse_args")
@patch("dewey.core.base_script.MockBaseScript.run")
def test_execute(mock_run: MagicMock, mock_parse_args: MagicMock, mock_base_script: MockBaseScript) -> None:
    """Test the execute method."""
    mock_parse_args.return_value = argparse.Namespace()
    mock_base_script.execute()
    mock_parse_args.assert_called_once()
    mock_run.assert_called_once()

    # Test KeyboardInterrupt
    mock_run.side_effect = KeyboardInterrupt
    with pytest.raises(SystemExit) as exc_info:
        mock_base_script.execute()
    assert exc_info.value.code == 1

    # Test Exception
    mock_run.side_effect = Exception("Run Error")
    with pytest.raises(SystemExit) as exc_info:
        mock_base_script.execute()
    assert exc_info.value.code == 1


def test_cleanup(mock_base_script: MockBaseScript) -> None:
    """Test the _cleanup method."""
    # Mock a database connection with a close method
    mock_db_conn = MagicMock()
    mock_base_script.db_conn = mock_db_conn

    mock_base_script._cleanup()
    mock_db_conn.close.assert_called_once()

    # Test with no database connection
    mock_base_script.db_conn = None
    mock_base_script._cleanup()  # Should not raise an error

    # Test with a database connection that raises an exception on close
    mock_db_conn.close.side_effect = Exception("Close Error")
    mock_base_script.db_conn = mock_db_conn
    mock_base_script._cleanup()  # Should log a warning but not raise an error


def test_get_path(mock_base_script: MockBaseScript) -> None:
    """Test the get_path method."""
    # Test with a relative path
    relative_path = "test_file.txt"
    expected_path = Path(PROJECT_ROOT) / relative_path
    assert mock_base_script.get_path(relative_path) == expected_path

    # Test with an absolute path
    absolute_path = "/tmp/test_file.txt"
    assert mock_base_script.get_path(absolute_path) == Path(absolute_path)


def test_get_config_value(mock_base_script: MockBaseScript, mock_config: Dict[str, Any]) -> None:
    """Test the get_config_value method."""
    # Test with a valid key
    assert mock_base_script.get_config_value("key1") == "value1"
    assert mock_base_script.get_config_value("key2") == "value2"

    # Test with a nested key
    mock_base_script.config = mock_config
    assert mock_base_script.get_config_value("core.logging.level") == "DEBUG"

    # Test with a default value
    assert mock_base_script.get_config_value("nonexistent_key", "default_value") == "default_value"

    # Test with a missing nested key
    assert mock_base_script.get_config_value("core.nonexistent_key", "default_value") == "default_value"

    # Test with no default value
    assert mock_base_script.get_config_value("nonexistent_key") is None
