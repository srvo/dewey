import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest
import yaml
from dotenv import load_dotenv

# Assuming BaseScript is in the parent directory of 'automation'
sys.path.append(str(Path(__file__).resolve().parents[4] / "src"))
from dewey.core.base_script import BaseScript  # noqa: E402

# Constants for testing
TEST_DATABASE_URL = "test_localhost:5432"
TEST_LLM_MODEL = "test_gpt-3.5-turbo"


class MockBaseScript(BaseScript):
    """Mock BaseScript class for testing."""

    def __init__(self, config_section: str = None, requires_db: bool = False, enable_llm: bool = False):
        super().__init__(config_section=config_section, requires_db=requires_db, enable_llm=enable_llm)

    def run(self) -> None:
        """Mock run method."""
        pass


# Fixtures
@pytest.fixture
def mock_fetch_data_from_db() -> Dict[str, str]:
    """Fixture to mock database fetch."""
    return {"data": "test data"}


@pytest.fixture
def mock_analyze_data_with_llm() -> Dict[str, str]:
    """Fixture to mock LLM analysis."""
    return {"analysis": "test analysis"}


@pytest.fixture
def mock_base_script(tmp_path: Path) -> MockBaseScript:
    """Fixture to create a mock BaseScript instance."""
    # Create a dummy config file
    config_data = {"test_section": {"param1": "value1"}}
    config_path = tmp_path / "test_config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config_data, f)

    # Mock the CONFIG_PATH attribute
    with patch("dewey.core.base_script.CONFIG_PATH", config_path):
        script = MockBaseScript(config_section="test_section")
        yield script


# Tests
def test_main_no_input(caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch,
                       mock_fetch_data_from_db: Dict[str, str],
                       mock_analyze_data_with_llm: Dict[str, str]) -> None:
    """Test main function with no input argument."""
    caplog.set_level(logging.INFO)

    # Mock functions
    monkeypatch.setattr("src.dewey.core.automation.tests.__init__.fetch_data_from_db",
                        lambda: mock_fetch_data_from_db)
    monkeypatch.setattr("src.dewey.core.automation.tests.__init__.analyze_data_with_llm",
                        lambda data: mock_analyze_data_with_llm)
    monkeypatch.setattr("sys.argv", ["__init__.py"])

    # Call main function
    import src.dewey.core.automation.tests.__init__ as automation_module
    automation_module.main()

    # Assertions
    assert "Starting script..." in caplog.text
    assert "Analysis: {'analysis': 'test analysis'}" in caplog.text
    assert "Script finished." in caplog.text


def test_main_with_input(caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch,
                        mock_fetch_data_from_db: Dict[str, str],
                        mock_analyze_data_with_llm: Dict[str, str]) -> None:
    """Test main function with input argument."""
    caplog.set_level(logging.INFO)

    # Mock functions
    monkeypatch.setattr("src.dewey.core.automation.tests.__init__.fetch_data_from_db",
                        lambda: mock_fetch_data_from_db)
    monkeypatch.setattr("src.dewey.core.automation.tests.__init__.analyze_data_with_llm",
                        lambda data: mock_analyze_data_with_llm)
    monkeypatch.setattr("sys.argv", ["__init__.py", "--input", "some_input"])

    # Call main function
    import src.dewey.core.automation.tests.__init__ as automation_module
    automation_module.main()

    # Assertions
    assert "Starting script..." in caplog.text
    assert "Analysis: {'analysis': 'test analysis'}" in caplog.text
    assert "Script finished." in caplog.text


def test_fetch_data_from_db(capfd: pytest.CaptureFixture[str]) -> None:
    """Test fetch_data_from_db function."""
    import src.dewey.core.automation.tests.__init__ as automation_module
    result = automation_module.fetch_data_from_db()
    captured = capfd.readouterr()

    assert "Fetching data from database..." in captured.out
    assert result == {"data": "some data"}


def test_analyze_data_with_llm(capfd: pytest.CaptureFixture[str]) -> None:
    """Test analyze_data_with_llm function."""
    import src.dewey.core.automation.tests.__init__ as automation_module
    data = {"data": "some data"}
    result = automation_module.analyze_data_with_llm(data)
    captured = capfd.readouterr()

    assert "Analyzing data with LLM..." in captured.out
    assert result == {"analysis": "some analysis"}


def test_base_script_initialization(mock_base_script: MockBaseScript) -> None:
    """Test BaseScript initialization."""
    assert mock_base_script.name == "MockBaseScript"
    assert mock_base_script.config_section == "test_section"
    assert mock_base_script.config["param1"] == "value1"
    assert mock_base_script.logger is not None


def test_base_script_get_path(mock_base_script: MockBaseScript) -> None:
    """Test BaseScript get_path method."""
    relative_path = "test_file.txt"
    absolute_path = "/tmp/test_file.txt"

    resolved_relative_path = mock_base_script.get_path(relative_path)
    resolved_absolute_path = mock_base_script.get_path(absolute_path)

    assert resolved_relative_path == Path(mock_base_script.PROJECT_ROOT / relative_path)
    assert resolved_absolute_path == Path(absolute_path)


def test_base_script_get_config_value(mock_base_script: MockBaseScript) -> None:
    """Test BaseScript get_config_value method."""
    value = mock_base_script.get_config_value("param1")
    default_value = mock_base_script.get_config_value("nonexistent_param", "default")
    none_value = mock_base_script.get_config_value("nonexistent_param")

    assert value == "value1"
    assert default_value == "default"
    assert none_value is None


def test_base_script_logging_level(caplog: pytest.LogCaptureFixture, tmp_path: Path) -> None:
    """Test BaseScript logging level configuration."""
    # Create a dummy config file with a specific log level
    config_data = {"core": {"logging": {"level": "DEBUG"}}}
    config_path = tmp_path / "test_config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config_data, f)

    # Mock the CONFIG_PATH attribute
    with patch("dewey.core.base_script.CONFIG_PATH", config_path):
        script = MockBaseScript()
        script.logger.debug("Debug message")
        script.logger.info("Info message")

    # Assert that the debug message is captured
    assert "Debug message" in caplog.text
    assert "Info message" in caplog.text


def test_base_script_config_section_not_found(caplog: pytest.LogCaptureFixture, tmp_path: Path) -> None:
    """Test BaseScript when the config section is not found."""
    caplog.set_level(logging.WARNING)

    # Create a dummy config file
    config_data = {"another_section": {"param1": "value1"}}
    config_path = tmp_path / "test_config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config_data, f)

    # Mock the CONFIG_PATH attribute
    with patch("dewey.core.base_script.CONFIG_PATH", config_path):
        script = MockBaseScript(config_section="test_section")

    # Assert that the warning message is logged
    assert "Config section 'test_section' not found in dewey.yaml. Using full config." in caplog.text
    assert script.config == config_data


def test_base_script_config_file_not_found(caplog: pytest.LogCaptureFixture) -> None:
    """Test BaseScript when the config file is not found."""
    caplog.set_level(logging.ERROR)

    # Mock the CONFIG_PATH attribute to a non-existent file
    with patch("dewey.core.base_script.CONFIG_PATH", "nonexistent_config.yaml"):
        with pytest.raises(FileNotFoundError):
            MockBaseScript()
        assert "Configuration file not found: nonexistent_config.yaml" in caplog.text


def test_base_script_config_file_invalid_yaml(caplog: pytest.LogCaptureFixture, tmp_path: Path) -> None:
    """Test BaseScript when the config file contains invalid YAML."""
    caplog.set_level(logging.ERROR)

    # Create a dummy config file with invalid YAML
    config_path = tmp_path / "test_config.yaml"
    with open(config_path, "w") as f:
        f.write("invalid yaml: -")

    # Mock the CONFIG_PATH attribute
    with patch("dewey.core.base_script.CONFIG_PATH", config_path):
        with pytest.raises(yaml.YAMLError):
            MockBaseScript()
        assert "Error parsing YAML configuration" in caplog.text


def test_base_script_db_connection_import_error(caplog: pytest.LogCaptureFixture, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test BaseScript when the database module cannot be imported."""
    caplog.set_level(logging.ERROR)

    # Mock the CONFIG_PATH attribute
    config_data = {"test_section": {"param1": "value1"}}
    config_path = tmp_path / "test_config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config_data, f)

    # Mock the CONFIG_PATH attribute
    with patch("dewey.core.base_script.CONFIG_PATH", config_path):
        # Mock the import of the database module to raise an ImportError
        monkeypatch.setattr("dewey.core.base_script.get_connection", side_effect=ImportError)
        script = MockBaseScript(requires_db=True)
        with pytest.raises(ImportError):
            script._initialize_db_connection()
        assert "Could not import database module. Is it installed?" in caplog.text


def test_base_script_llm_client_import_error(caplog: pytest.LogCaptureFixture, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test BaseScript when the LLM module cannot be imported."""
    caplog.set_level(logging.ERROR)

    # Mock the CONFIG_PATH attribute
    config_data = {"test_section": {"param1": "value1"}}
    config_path = tmp_path / "test_config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config_data, f)

    # Mock the CONFIG_PATH attribute
    with patch("dewey.core.base_script.CONFIG_PATH", config_path):
        # Mock the import of the LLM module to raise an ImportError
        monkeypatch.setattr("dewey.core.base_script.get_llm_client", side_effect=ImportError)
        script = MockBaseScript(enable_llm=True)
        with pytest.raises(ImportError):
            script._initialize_llm_client()
        assert "Could not import LLM module. Is it installed?" in caplog.text


def test_base_script_db_connection_failure(caplog: pytest.LogCaptureFixture, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test BaseScript when the database connection fails."""
    caplog.set_level(logging.ERROR)

    # Create a dummy config file
    config_data = {"test_section": {"param1": "value1"}}
    config_path = tmp_path / "test_config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config_data, f)

    # Mock the CONFIG_PATH attribute
    with patch("dewey.core.base_script.CONFIG_PATH", config_path):
        # Mock the database connection to raise an Exception
        monkeypatch.setattr("dewey.core.db.connection.get_connection", side_effect=Exception("Connection failed"))
        script = MockBaseScript(requires_db=True)
        with pytest.raises(Exception, match="Connection failed"):
            script._initialize_db_connection()
        assert "Failed to initialize database connection: Connection failed" in caplog.text


def test_base_script_llm_client_failure(caplog: pytest.LogCaptureFixture, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test BaseScript when the LLM client initialization fails."""
    caplog.set_level(logging.ERROR)

    # Create a dummy config file
    config_data = {"test_section": {"param1": "value1"}}
    config_path = tmp_path / "test_config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config_data, f)

    # Mock the CONFIG_PATH attribute
    with patch("dewey.core.base_script.CONFIG_PATH", config_path):
        # Mock the LLM client initialization to raise an Exception
        monkeypatch.setattr("dewey.llm.llm_utils.get_llm_client", side_effect=Exception("Client failed"))
        script = MockBaseScript(enable_llm=True)
        with pytest.raises(Exception, match="Client failed"):
            script._initialize_llm_client()
        assert "Failed to initialize LLM client: Client failed" in caplog.text


def test_base_script_setup_argparse(mock_base_script: MockBaseScript) -> None:
    """Test BaseScript setup_argparse method."""
    parser = mock_base_script.setup_argparse()
    assert isinstance(parser, argparse.ArgumentParser)
    assert parser.description == mock_base_script.description
    assert any(action.dest == "config" for action in parser._actions)
    assert any(action.dest == "log_level" for action in parser._actions)


def test_base_script_setup_argparse_with_db(mock_base_script: MockBaseScript) -> None:
    """Test BaseScript setup_argparse method with database."""
    mock_base_script.requires_db = True
    parser = mock_base_script.setup_argparse()
    assert any(action.dest == "db_connection_string" for action in parser._actions)


def test_base_script_setup_argparse_with_llm(mock_base_script: MockBaseScript) -> None:
    """Test BaseScript setup_argparse method with LLM."""
    mock_base_script.enable_llm = True
    parser = mock_base_script.setup_argparse()
    assert any(action.dest == "llm_model" for action in parser._actions)


def test_base_script_parse_args_log_level(mock_base_script: MockBaseScript, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    """Test BaseScript parse_args method with log level."""
    caplog.set_level(logging.DEBUG)
    monkeypatch.setattr("sys.argv", ["test_script.py", "--log-level", "DEBUG"])
    args = mock_base_script.parse_args()
    assert args.log_level == "DEBUG"
    assert mock_base_script.logger.level == logging.DEBUG
    assert "Log level set to DEBUG" in caplog.text


def test_base_script_parse_args_config_file(mock_base_script: MockBaseScript, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test BaseScript parse_args method with config file."""
    caplog.set_level(logging.INFO)

    # Create a dummy config file
    config_data = {"another_section": {"param1": "value1"}}
    config_path = tmp_path / "test_config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config_data, f)

    monkeypatch.setattr("sys.argv", ["test_script.py", "--config", str(config_path)])
    args = mock_base_script.parse_args()
    assert args.config == str(config_path)
    assert mock_base_script.config == config_data
    assert "Loaded configuration from" in caplog.text


def test_base_script_parse_args_config_file_not_found(mock_base_script: MockBaseScript, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    """Test BaseScript parse_args method with config file not found."""
    caplog.set_level(logging.ERROR)
    monkeypatch.setattr("sys.argv", ["test_script.py", "--config", "nonexistent_config.yaml"])
    with pytest.raises(SystemExit) as excinfo:
        mock_base_script.parse_args()
    assert excinfo.value.code == 1
    assert "Configuration file not found: nonexistent_config.yaml" in caplog.text


def test_base_script_parse_args_db_connection_string(mock_base_script: MockBaseScript, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    """Test BaseScript parse_args method with database connection string."""
    caplog.set_level(logging.INFO)
    mock_base_script.requires_db = True
    monkeypatch.setattr("sys.argv", ["test_script.py", "--db-connection-string", "test_connection_string"])
    with patch("dewey.core.db.connection.get_connection") as mock_get_connection:
        args = mock_base_script.parse_args()
        assert args.db_connection_string == "test_connection_string"
        mock_get_connection.assert_called_once_with({"connection_string": "test_connection_string"})
        assert "Using custom database connection" in caplog.text


def test_base_script_parse_args_llm_model(mock_base_script: MockBaseScript, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    """Test BaseScript parse_args method with LLM model."""
    caplog.set_level(logging.INFO)
    mock_base_script.enable_llm = True
    monkeypatch.setattr("sys.argv", ["test_script.py", "--llm-model", "test_llm_model"])
    with patch("dewey.llm.llm_utils.get_llm_client") as mock_get_llm_client:
        args = mock_base_script.parse_args()
        assert args.llm_model == "test_llm_model"
        mock_get_llm_client.assert_called_once_with({"model": "test_llm_model"})
        assert "Using custom LLM model: test_llm_model" in caplog.text


def test_base_script_execute_keyboard_interrupt(mock_base_script: MockBaseScript, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    """Test BaseScript execute method with KeyboardInterrupt."""
    caplog.set_level(logging.WARNING)
    monkeypatch.setattr("src.dewey.core.base_script.BaseScript.parse_args", side_effect=KeyboardInterrupt)
    with pytest.raises(SystemExit) as excinfo:
        mock_base_script.execute()
    assert excinfo.value.code == 1
    assert "Script interrupted by user" in caplog.text


def test_base_script_execute_exception(mock_base_script: MockBaseScript, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    """Test BaseScript execute method with Exception."""
    caplog.set_level(logging.ERROR)
    monkeypatch.setattr("src.dewey.core.base_script.BaseScript.run", side_effect=Exception("Execution failed"))
    with pytest.raises(SystemExit) as excinfo:
        mock_base_script.execute()
    assert excinfo.value.code == 1
    assert "Error executing script: Execution failed" in caplog.text


def test_base_script_cleanup(mock_base_script: MockBaseScript, caplog: pytest.LogCaptureFixture) -> None:
    """Test BaseScript cleanup method."""
    caplog.set_level(logging.DEBUG)
    mock_base_script.requires_db = True
    mock_base_script.db_conn = pytest.mock.Mock()
    mock_base_script._cleanup()
    mock_base_script.db_conn.close.assert_called_once()
    assert "Closing database connection" in caplog.text


def test_base_script_cleanup_db_error(mock_base_script: MockBaseScript, caplog: pytest.LogCaptureFixture) -> None:
    """Test BaseScript cleanup method with database error."""
    caplog.set_level(logging.WARNING)
    mock_base_script.requires_db = True
    mock_base_script.db_conn = pytest.mock.Mock()
    mock_base_script.db_conn.close.side_effect = Exception("Close failed")
    mock_base_script._cleanup()
    mock_base_script.db_conn.close.assert_called_once()
    assert "Error closing database connection: Close failed" in caplog.text


def test_load_dotenv_called(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test that load_dotenv is called during BaseScript initialization."""
    # Create a dummy config file
    config_data = {"test_section": {"param1": "value1"}}
    config_path = tmp_path / "test_config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config_data, f)

    # Mock the CONFIG_PATH attribute
    with patch("dewey.core.base_script.CONFIG_PATH", config_path):
        with patch("dewey.core.base_script.load_dotenv") as mock_load_dotenv:
            MockBaseScript(config_section="test_section")
            mock_load_dotenv.assert_called_once_with(Path(__file__).resolve().parents[4] / ".env")
