import logging
from unittest.mock import patch

import pytest

from dewey.core.crm.docs import DocsModule
from dewey.core.base_script import BaseScript


class TestDocsModule:
    """Tests for the DocsModule class."""

    @pytest.fixture
    def docs_module(self) -> DocsModule:
        """Fixture for creating a DocsModule instance."""
        return DocsModule()

    def test_initialization(self, docs_module: DocsModule) -> None:
        """Test that the DocsModule is initialized correctly."""
        assert docs_module.name == "CRM Docs Module"
        assert docs_module.description == "Manages CRM documentation tasks."
        assert docs_module.config_section == "crm_docs"
        assert isinstance(docs_module, BaseScript)

    def test_run_method(
        self, docs_module: DocsModule, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test the run method of the DocsModule."""
        caplog.set_level(logging.INFO)
        docs_module.run()
        assert "Running CRM Docs Module..." in caplog.text
        assert "Example configuration value: default_value" in caplog.text
        assert "CRM Docs Module completed." in caplog.text

    def test_run_method_with_config_value(
        self, docs_module: DocsModule, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test the run method when a config value is available."""
        caplog.set_level(logging.INFO)
        with patch.object(docs_module, "get_config_value", return_value="config_value"):
            docs_module.run()
        assert "Example configuration value: config_value" in caplog.text

    def test_get_config_value_existing_key(self, docs_module: DocsModule) -> None:
        """Test getting an existing config value."""
        with patch.object(docs_module, "config", {"example_setting": "test_value"}):
            value = docs_module.get_config_value("example_setting")
            assert value == "test_value"

    def test_get_config_value_nonexistent_key(self, docs_module: DocsModule) -> None:
        """Test getting a non-existent config value with a default."""
        value = docs_module.get_config_value("nonexistent_setting", "default_value")
        assert value == "default_value"

    def test_get_config_value_no_default(self, docs_module: DocsModule) -> None:
        """Test getting a non-existent config value without a default."""
        value = docs_module.get_config_value("nonexistent_setting")
        assert value is None

    def test_get_config_value_nested_key(self, docs_module: DocsModule) -> None:
        """Test getting a nested config value."""
        with patch.object(
            docs_module, "config", {"nested": {"example_setting": "nested_value"}}
        ):
            value = docs_module.get_config_value("nested.example_setting")
            assert value == "nested_value"

    def test_get_config_value_nested_key_missing(self, docs_module: DocsModule) -> None:
        """Test getting a nested config value when a level is missing."""
        with patch.object(docs_module, "config", {"nested": {}}):
            value = docs_module.get_config_value(
                "nested.missing_setting", "default_value"
            )
            assert value == "default_value"

    def test_get_config_value_empty_config(self, docs_module: DocsModule) -> None:
        """Test getting a config value when the config is empty."""
        with patch.object(docs_module, "config", {}):
            value = docs_module.get_config_value("example_setting", "default_value")
            assert value == "default_value"

    def test_get_config_value_type_error(self, docs_module: DocsModule) -> None:
        """Test getting a config value when a TypeError occurs."""
        with patch.object(docs_module, "config", {"example_setting": 123}):
            with patch.object(BaseScript, "get_config_value", side_effect=TypeError):
                value = docs_module.get_config_value("example_setting", "default_value")
                assert value == "default_value"
