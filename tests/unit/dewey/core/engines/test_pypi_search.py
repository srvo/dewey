import logging
from unittest.mock import patch
from typing import Any
import pytest

from dewey.core.engines.pypi_search import PypiSearch
from dewey.core.base_script import BaseScript


class MockBaseScript(BaseScript):
    def __init__(self, config_section: str = None, requires_db: bool = False, enable_llm: bool = False) -> None:
        super().__init__(config_section=config_section, requires_db=requires_db, enable_llm=enable_llm)

    def run(self) -> None:
        pass


@pytest.fixture
def mock_base_script(monkeypatch: pytest.MonkeyPatch) -> MockBaseScript:
    """Fixture to create a mock BaseScript instance."""
    # Mock the _load_config method to avoid loading the actual config file
    monkeypatch.setattr(BaseScript, '_load_config', lambda self: {"package_name": "requests"})
    return MockBaseScript()


@pytest.fixture
def pypi_search(mock_base_script: MockBaseScript) -> PypiSearch:
    """Fixture to create a PypiSearch instance."""
    return PypiSearch()


def test_pypi_search_initialization(pypi_search: PypiSearch) -> None:
    """Test that PypiSearch is initialized correctly."""
    assert pypi_search.name == "PypiSearch"
    assert pypi_search.config_section is None
    assert pypi_search.requires_db is False
    assert pypi_search.enable_llm is False


def test_pypi_search_run_success(pypi_search: PypiSearch, caplog: pytest.LogCaptureFixture) -> None:
    """Test that PypiSearch.run() executes successfully."""
    caplog.set_level(logging.INFO)
    pypi_search.run()
    assert "Searching PyPI for package: requests" in caplog.text
    assert "PyPI search completed." in caplog.text


def test_pypi_search_run_exception(pypi_search: PypiSearch, caplog: pytest.LogCaptureFixture) -> None:
    """Test that PypiSearch.run() handles exceptions correctly."""
    caplog.set_level(logging.ERROR)
    with patch.object(pypi_search, 'get_config_value', side_effect=Exception("Config error")):
        pypi_search.run()
    assert "An error occurred during PyPI search: Config error" in caplog.text
    assert "Traceback" in caplog.text


def test_pypi_search_get_config_value(pypi_search: PypiSearch, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that PypiSearch.get_config_value() retrieves config values correctly."""
    monkeypatch.setattr(pypi_search, 'config', {'package_name': 'beautifulsoup4'})
    package_name = pypi_search.get_config_value('package_name')
    assert package_name == 'beautifulsoup4'


def test_pypi_search_get_config_value_default(pypi_search: PypiSearch) -> None:
    """Test that PypiSearch.get_config_value() returns the default value if the key is not found."""
    default_value = pypi_search.get_config_value('non_existent_key', 'default')
    assert default_value == 'default'


def test_pypi_search_get_config_value_nested(pypi_search: PypiSearch, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that PypiSearch.get_config_value() retrieves nested config values correctly."""
    monkeypatch.setattr(pypi_search, 'config', {'nested': {'package_name': 'sqlalchemy'}})
    package_name = pypi_search.get_config_value('nested.package_name')
    assert package_name == 'sqlalchemy'


def test_pypi_search_get_config_value_nested_default(pypi_search: PypiSearch) -> None:
    """Test that PypiSearch.get_config_value() returns the default value for nested keys if not found."""
    default_value = pypi_search.get_config_value('nested.non_existent_key', 'default')
    assert default_value == 'default'


def test_pypi_search_get_config_value_missing_intermediate(pypi_search: PypiSearch) -> None:
    """Test that PypiSearch.get_config_value() returns the default value if an intermediate key is missing."""
    default_value = pypi_search.get_config_value('missing.intermediate.key', 'default')
    assert default_value == 'default'

