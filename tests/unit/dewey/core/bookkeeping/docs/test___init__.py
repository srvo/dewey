import logging
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.bookkeeping.docs import DocsModule


class TestDocsModule:
    """Test suite for the DocsModule class."""

    @pytest.fixture
    def mock_base_script(self) -> MagicMock:
        """Fixture to mock the BaseScript class."""
        with patch("dewey.core.bookkeeping.docs.BaseScript", autospec=True) as mock:
            yield mock

    @pytest.fixture
    def docs_module(self) -> DocsModule:
        """Fixture to create a DocsModule instance."""
        return DocsModule(name="TestDocs")

    def test_docs_module_initialization(self, mock_base_script: MagicMock) -> None:
        """Test that DocsModule initializes correctly."""
        docs_module = DocsModule(name="TestDocs", description="Test Description")

        mock_base_script.assert_called_once_with(
            name="TestDocs", description="Test Description", config_section="docs"
        )
        assert docs_module.name == "TestDocs"
        assert docs_module.description == "Test Description"

    def test_run_method_no_errors(
        self, docs_module: DocsModule, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test the run method executes without errors."""
        caplog.set_level(logging.INFO)
        docs_module.get_config_value = MagicMock(return_value="test_value")
        docs_module.run()

        assert "Running the Docs module..." in caplog.text
        assert "Example config value: test_value" in caplog.text
        assert "Documentation tasks completed." in caplog.text

    def test_run_method_with_error(
        self, docs_module: DocsModule, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test the run method handles errors correctly."""
        caplog.set_level(logging.ERROR)
        docs_module.get_config_value = MagicMock(side_effect=ValueError("Config error"))

        with pytest.raises(ValueError, match="Config error"):
            docs_module.run()

        assert "An error occurred during documentation: Config error" in caplog.text

    def test_get_config_value_exists(self, docs_module: DocsModule) -> None:
        """Test that get_config_value returns the correct value when the key exists."""
        docs_module.config = {"test_key": "test_value"}
        value = docs_module.get_config_value("test_key")
        assert value == "test_value"

    def test_get_config_value_does_not_exist_with_default(
        self, docs_module: DocsModule
    ) -> None:
        """Test that get_config_value returns the default value when the key does not exist."""
        docs_module.config = {}
        default_value = "default_value"
        value = docs_module.get_config_value("nonexistent_key", default_value)
        assert value == default_value

    def test_get_config_value_does_not_exist_without_default(
        self, docs_module: DocsModule
    ) -> None:
        """Test that get_config_value returns None when the key does not exist and no default is provided."""
        docs_module.config = {}
        value = docs_module.get_config_value("nonexistent_key")
        assert value is None

    def test_get_config_value_nested_key_exists(self, docs_module: DocsModule) -> None:
        """Test that get_config_value returns the correct value for a nested key."""
        docs_module.config = {"nested": {"test_key": "test_value"}}
        value = docs_module.get_config_value("nested.test_key")
        assert value == "test_value"

    def test_get_config_value_nested_key_does_not_exist(
        self, docs_module: DocsModule
    ) -> None:
        """Test that get_config_value returns the default value for a nested key that does not exist."""
        docs_module.config = {"nested": {}}
        default_value = "default_value"
        value = docs_module.get_config_value("nested.nonexistent_key", default_value)
        assert value == default_value

    def test_get_config_value_intermediate_key_does_not_exist(
        self, docs_module: DocsModule
    ) -> None:
        """Test that get_config_value returns the default value when an intermediate key in the path does not exist."""
        docs_module.config = {}
        default_value = "default_value"
        value = docs_module.get_config_value("nonexistent.test_key", default_value)
        assert value == default_value

    def test_get_config_value_empty_key(self, docs_module: DocsModule) -> None:
        """Test that get_config_value returns the entire config when an empty key is provided."""
        docs_module.config = {"test_key": "test_value"}
        value = docs_module.get_config_value("")
        assert (
            value is None
        )  # Or handle as you see fit, perhaps return the entire config?

    def test_get_config_value_config_is_none(self, docs_module: DocsModule) -> None:
        """Test that get_config_value handles the case where the config is None."""
        docs_module.config = None  # type: ignore[assignment]
        default_value = "default_value"
        value = docs_module.get_config_value("test_key", default_value)
        assert value == default_value

    def test_get_config_value_config_value_is_none(
        self, docs_module: DocsModule
    ) -> None:
        """Test that get_config_value handles the case where the config value is None."""
        docs_module.config = {"test_key": None}
        value = docs_module.get_config_value("test_key")
        assert value is None
