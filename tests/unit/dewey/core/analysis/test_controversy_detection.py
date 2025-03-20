import logging
from typing import Any
from unittest.mock import patch

import pytest

from dewey.core.analysis.controversy_detection import ControversyDetection
from dewey.core.base_script import BaseScript


class MockBaseScript(BaseScript):
    """Mock BaseScript class for testing."""

    def __init__(self, config_section: str = "test_config") -> None:
        """Function __init__."""
        super().__init__(config_section=config_section)

    def run(self) -> None:
        """Function run."""
        pass


@pytest.fixture
def controversy_detector() -> ControversyDetection:
    """Fixture to create a ControversyDetection instance."""
    return ControversyDetection()


@pytest.fixture
def mock_base_script() -> MockBaseScript:
    """Fixture to create a MockBaseScript instance."""
    return MockBaseScript()


def test_controversy_detection_initialization(
    controversy_detector: ControversyDetection,
) -> None:
    """Test the initialization of the ControversyDetection class."""
    assert isinstance(controversy_detector, ControversyDetection)
    assert controversy_detector.name == "ControversyDetection"
    assert controversy_detector.config is not None
    assert controversy_detector.logger is not None


def test_controversy_detection_run_no_data(
    controversy_detector: ControversyDetection, caplog: pytest.LogCaptureFixture
) -> None:
    """Test the run method with no input data."""
    caplog.set_level(logging.INFO)
    result = controversy_detector.run()
    assert result is None
    assert "Starting controversy detection..." in caplog.text
    assert "Controversy detection complete." in caplog.text


def test_controversy_detection_run_with_data(
    controversy_detector: ControversyDetection, caplog: pytest.LogCaptureFixture
) -> None:
    """Test the run method with input data."""
    caplog.set_level(logging.INFO)
    data = {"text": "This is a controversial topic."}
    result = controversy_detector.run(data)
    assert result is None
    assert "Starting controversy detection..." in caplog.text
    assert "Controversy detection complete." in caplog.text


def test_controversy_detection_config_access(
    controversy_detector: ControversyDetection, caplog: pytest.LogCaptureFixture
) -> None:
    """Test accessing a configuration value."""
    caplog.set_level(logging.DEBUG)
    controversy_detector.run()
    assert "Some config value:" in caplog.text


def test_controversy_detection_execute(
    controversy_detector: ControversyDetection, caplog: pytest.LogCaptureFixture
) -> None:
    """Test the execute method."""
    caplog.set_level(logging.INFO)
    with (
        patch.object(ControversyDetection, "parse_args") as mock_parse_args,
        patch.object(ControversyDetection, "run") as mock_run,
        patch.object(ControversyDetection, "_cleanup") as mock_cleanup,
    ):
        mock_parse_args.return_value = None
        mock_run.return_value = None
        controversy_detector.execute()
        assert "Starting execution of ControversyDetection" in caplog.text
        assert "Completed execution of ControversyDetection" in caplog.text
        mock_parse_args.assert_called_once()
        mock_run.assert_called_once()
        mock_cleanup.assert_called_once()


def test_controversy_detection_execute_keyboard_interrupt(
    controversy_detector: ControversyDetection, caplog: pytest.LogCaptureFixture
) -> None:
    """Test the execute method with a KeyboardInterrupt."""
    caplog.set_level(logging.WARNING)
    with (
        patch.object(ControversyDetection, "parse_args") as mock_parse_args,
        patch.object(ControversyDetection, "run") as mock_run,
    ):
        mock_parse_args.return_value = None
        mock_run.side_effect = KeyboardInterrupt
        with pytest.raises(SystemExit) as exc_info:
            controversy_detector.execute()
        assert exc_info.value.code == 1
        assert "Script interrupted by user" in caplog.text


def test_controversy_detection_execute_exception(
    controversy_detector: ControversyDetection, caplog: pytest.LogCaptureFixture
) -> None:
    """Test the execute method with an exception."""
    caplog.set_level(logging.ERROR)
    with (
        patch.object(ControversyDetection, "parse_args") as mock_parse_args,
        patch.object(ControversyDetection, "run") as mock_run,
    ):
        mock_parse_args.return_value = None
        mock_run.side_effect = ValueError("Test exception")
        with pytest.raises(SystemExit) as exc_info:
            controversy_detector.execute()
        assert exc_info.value.code == 1
        assert "Error executing script: Test exception" in caplog.text


def test_get_path(controversy_detector: ControversyDetection) -> None:
    """Test the get_path method."""
    project_root = controversy_detector.get_path(".")
    assert project_root.is_dir()

    absolute_path = controversy_detector.get_path("/tmp")
    assert str(absolute_path) == "/tmp"


def test_get_config_value(mock_base_script: MockBaseScript) -> None:
    """Test the get_config_value method."""
    config_value = mock_base_script.get_config_value("test_key", "default_value")
    assert config_value == "test_value"

    nested_config_value = mock_base_script.get_config_value(
        "nested.test_key", "default_value"
    )
    assert nested_config_value == "nested_value"

    default_value = mock_base_script.get_config_value(
        "nonexistent_key", "default_value"
    )
    assert default_value == "default_value"

    none_default_value = mock_base_script.get_config_value("nonexistent_key")
    assert none_default_value is None


# Mock configuration for testing
@pytest.fixture(scope="session")
def test_config() -> Dict[str, Any]:
    """Fixture for test configuration."""
    return {"test_key": "test_value", "nested": {"test_key": "nested_value"}}


@pytest.fixture
def mock_config(monkeypatch: pytest.MonkeyPatch, test_config: Dict[str, Any]) -> None:
    """Fixture to mock the config attribute of BaseScript."""
    monkeypatch.setattr(BaseScript, "config", test_config)
