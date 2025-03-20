import logging
from unittest.mock import patch

import pytest

from dewey.core.engines.motherduck import MotherDuck
from dewey.core.base_script import BaseScript


class MockBaseScript(BaseScript):
    def __init__(self, config_section: str = 'motherduck', requires_db: bool = False, enable_llm: bool = False):
        super().__init__(config_section=config_section, requires_db=requires_db, enable_llm=enable_llm)

    def run(self) -> None:
        pass


@pytest.fixture
def motherduck_engine() -> MotherDuck:
    """Fixture to create a MotherDuck engine instance."""
    return MotherDuck()


@pytest.fixture
def mock_base_script() -> MockBaseScript:
    """Fixture to create a MockBaseScript instance."""
    return MockBaseScript()


def test_motherduck_initialization(motherduck_engine: MotherDuck) -> None:
    """Test that the MotherDuck engine initializes correctly."""
    assert isinstance(motherduck_engine, MotherDuck)
    assert motherduck_engine.name == "MotherDuck"
    assert motherduck_engine.config_section == "motherduck"
    assert motherduck_engine.logger is not None


def test_motherduck_run_method(motherduck_engine: MotherDuck, caplog: pytest.LogCaptureFixture) -> None:
    """Test the run method of the MotherDuck engine."""
    with caplog.at_level(logging.INFO):
        motherduck_engine.run()
    assert "Running MotherDuck script" in caplog.text
    assert "MotherDuck script completed" in caplog.text


def test_motherduck_run_method_api_token_debug(motherduck_engine: MotherDuck, caplog: pytest.LogCaptureFixture) -> None:
    """Test that the API token is logged at the debug level in the run method."""
    with patch.object(motherduck_engine, 'get_config_value', return_value='test_token'):
        with caplog.at_level(logging.DEBUG):
            motherduck_engine.run()
    assert "API Token: test_token" in caplog.text


def test_get_config_value_existing_key(mock_base_script: MockBaseScript) -> None:
    """Test that get_config_value returns the correct value for an existing key."""
    mock_base_script.config = {"test_key": "test_value"}
    assert mock_base_script.get_config_value("test_key") == "test_value"


def test_get_config_value_nested_key(mock_base_script: MockBaseScript) -> None:
    """Test that get_config_value returns the correct value for a nested key."""
    mock_base_script.config = {"nested": {"test_key": "test_value"}}
    assert mock_base_script.get_config_value("nested.test_key") == "test_value"


def test_get_config_value_default_value(mock_base_script: MockBaseScript) -> None:
    """Test that get_config_value returns the default value for a non-existing key."""
    mock_base_script.config = {}
    assert mock_base_script.get_config_value("non_existing_key", "default_value") == "default_value"


def test_get_config_value_non_existing_key(mock_base_script: MockBaseScript) -> None:
    """Test that get_config_value returns None for a non-existing key when no default is provided."""
    mock_base_script.config = {}
    assert mock_base_script.get_config_value("non_existing_key") is None


def test_get_config_value_intermediate_key_missing(mock_base_script: MockBaseScript) -> None:
    """Test that get_config_value returns the default value when an intermediate key is missing."""
    mock_base_script.config = {"existing": {}}
    assert mock_base_script.get_config_value("existing.missing.key", "default_value") == "default_value"


def test_get_config_value_config_is_none(mock_base_script: MockBaseScript) -> None:
    """Test that get_config_value returns the default value when config is None."""
    mock_base_script.config = None
    assert mock_base_script.get_config_value("any_key", "default_value") == "default_value"


def test_get_config_value_empty_key(mock_base_script: MockBaseScript) -> None:
    """Test that get_config_value returns the entire config when an empty key is provided."""
    mock_base_script.config = {"test_key": "test_value"}
    assert mock_base_script.get_config_value("") == {"test_key": "test_value"}


def test_get_config_value_invalid_key_type(mock_base_script: MockBaseScript) -> None:
    """Test that get_config_value returns the default value when the key is not a string."""
    mock_base_script.config = {"test_key": "test_value"}
    with pytest.raises(AttributeError):
        mock_base_script.get_config_value(123, "default_value")  # type: ignore


def test_get_path_absolute_path(mock_base_script: MockBaseScript) -> None:
    """Test that get_path returns the same path when an absolute path is provided."""
    absolute_path = "/absolute/path"
    assert mock_base_script.get_path(absolute_path) == Path(absolute_path)


def test_get_path_relative_path(mock_base_script: MockBaseScript) -> None:
    """Test that get_path returns the correct absolute path when a relative path is provided."""
    relative_path = "relative/path"
    expected_path = mock_base_script.PROJECT_ROOT / relative_path
    assert mock_base_script.get_path(relative_path) == expected_path


def test_get_path_pathlib_path(mock_base_script: MockBaseScript) -> None:
    """Test that get_path works correctly with pathlib.Path objects."""
    pathlib_path = Path("pathlib/path")
    expected_path = mock_base_script.PROJECT_ROOT / pathlib_path
    assert mock_base_script.get_path(pathlib_path) == expected_path


def test_get_path_empty_path(mock_base_script: MockBaseScript) -> None:
    """Test that get_path returns the project root when an empty path is provided."""
    expected_path = mock_base_script.PROJECT_ROOT
    assert mock_base_script.get_path("") == expected_path


def test_get_path_parent_directory(mock_base_script: MockBaseScript) -> None:
    """Test that get_path correctly resolves paths with parent directory references."""
    relative_path = "../relative/path"
    expected_path = mock_base_script.PROJECT_ROOT.parent / "relative" / "path"
    assert mock_base_script.get_path(relative_path) == expected_path


def test_get_path_home_directory(mock_base_script: MockBaseScript) -> None:
    """Test that get_path does not expand the home directory."""
    home_path = "~/relative/path"
    expected_path = mock_base_script.PROJECT_ROOT / home_path
    assert mock_base_script.get_path(home_path) == expected_path
