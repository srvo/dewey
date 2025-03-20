"""Tests for dewey.core.analysis.controversy_detection."""

import logging
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.analysis.controversy_detection import ControversyDetection
from dewey.core.base_script import BaseScript


@pytest.fixture
def mock_base_script() -> MagicMock:
    """Fixture to create a mock BaseScript instance."""
    mock_script = MagicMock(spec=BaseScript)
    mock_script.get_config_value.return_value = "test_value"
    mock_script.logger = MagicMock()
    return mock_script


@pytest.fixture
def controversy_detector(mock_base_script: MagicMock) -> ControversyDetection:
    """Fixture to create a ControversyDetection instance."""
    with patch(
        "dewey.core.analysis.controversy_detection.BaseScript.__init__",
        return_value=None,
    ):
        detector = ControversyDetection()
        detector.config = {"utils": {"example_config": "test_config_value"}}
        detector.logger = MagicMock()
        detector.db_conn = MagicMock()
        detector.llm_client = MagicMock()
        return detector


def test_controversy_detection_initialization(
    controversy_detector: ControversyDetection,
) -> None:
    """Test the initialization of the ControversyDetection class."""
    assert isinstance(controversy_detector, ControversyDetection)
    assert controversy_detector.name == "ControversyDetection"
    assert controversy_detector.config is not None
    assert controversy_detector.logger is not None


def test_controversy_detection_run_no_data(
    controversy_detector: ControversyDetection,
) -> None:
    """Test the run method with no input data."""
    controversy_detector.logger.info.return_value = None
    result = controversy_detector.run()
    assert result is None
    controversy_detector.logger.info.assert_called()


def test_controversy_detection_run_with_data(
    controversy_detector: ControversyDetection,
) -> None:
    """Test the run method with input data."""
    controversy_detector.logger.info.return_value = None
    data = {"text": "This is a controversial topic."}
    result = controversy_detector.run(data)
    assert result is None
    controversy_detector.logger.info.assert_called()


def test_controversy_detection_config_access(
    controversy_detector: ControversyDetection,
) -> None:
    """Test accessing a configuration value."""
    controversy_detector.get_config_value = MagicMock(return_value="config_value")
    controversy_detector.run()
    controversy_detector.get_config_value.assert_called_with(
        "utils.example_config", "default_value"
    )


@patch("dewey.core.analysis.controversy_detection.llm_utils.generate_response")
def test_controversy_detection_llm_usage(
    mock_generate_response: MagicMock, controversy_detector: ControversyDetection
) -> None:
    """Test the LLM usage in the run method."""
    mock_generate_response.return_value = "LLM Response"
    data = {"text": "Test text"}
    result = controversy_detector.run(data)
    assert result == "LLM Response"
    mock_generate_response.assert_called()


def test_controversy_detection_db_usage(
    controversy_detector: ControversyDetection,
) -> None:
    """Test the database usage in the run method."""
    controversy_detector.db_conn.execute = MagicMock(return_value="DB Result")
    controversy_detector.run()
    controversy_detector.db_conn.execute.assert_called()


@patch("dewey.core.analysis.controversy_detection.ControversyDetection.parse_args")
@patch("dewey.core.analysis.controversy_detection.ControversyDetection.run")
@patch("dewey.core.analysis.controversy_detection.ControversyDetection._cleanup")
def test_controversy_detection_execute(
    mock_cleanup: MagicMock,
    mock_run: MagicMock,
    mock_parse_args: MagicMock,
    controversy_detector: ControversyDetection,
) -> None:
    """Test the execute method."""
    mock_parse_args.return_value = None
    mock_run.return_value = None
    controversy_detector.execute()
    mock_parse_args.assert_called_once()
    mock_run.assert_called_once()
    mock_cleanup.assert_called_once()


@patch("dewey.core.analysis.controversy_detection.ControversyDetection.parse_args")
@patch("dewey.core.analysis.controversy_detection.ControversyDetection.run")
def test_controversy_detection_execute_keyboard_interrupt(
    mock_run: MagicMock,
    mock_parse_args: MagicMock,
    controversy_detector: ControversyDetection,
) -> None:
    """Test the execute method with a KeyboardInterrupt."""
    mock_parse_args.return_value = None
    mock_run.side_effect = KeyboardInterrupt
    with pytest.raises(SystemExit) as exc_info:
        controversy_detector.execute()
    assert exc_info.value.code == 1


@patch("dewey.core.analysis.controversy_detection.ControversyDetection.parse_args")
@patch("dewey.core.analysis.controversy_detection.ControversyDetection.run")
def test_controversy_detection_execute_exception(
    mock_run: MagicMock,
    mock_parse_args: MagicMock,
    controversy_detector: ControversyDetection,
) -> None:
    """Test the execute method with an exception."""
    mock_parse_args.return_value = None
    mock_run.side_effect = ValueError("Test exception")
    with pytest.raises(SystemExit) as exc_info:
        controversy_detector.execute()
    assert exc_info.value.code == 1


def test_get_path(controversy_detector: ControversyDetection) -> None:
    """Test the get_path method."""
    project_root = controversy_detector.get_path(".")
    assert project_root.is_dir()

    absolute_path = controversy_detector.get_path("/tmp")
    assert str(absolute_path) == "/tmp"


def test_get_config_value(controversy_detector: ControversyDetection) -> None:
    """Test the get_config_value method."""
    controversy_detector.config = {"test_key": "test_value", "nested": {"test_key": "nested_value"}}
    config_value = controversy_detector.get_config_value("test_key", "default_value")
    assert config_value == "test_value"

    nested_config_value = controversy_detector.get_config_value(
        "nested.test_key", "default_value"
    )
    assert nested_config_value == "nested_value"

    default_value = controversy_detector.get_config_value(
        "nonexistent_key", "default_value"
    )
    assert default_value == "default_value"

    none_default_value = controversy_detector.get_config_value("nonexistent_key")
    assert none_default_value is None
