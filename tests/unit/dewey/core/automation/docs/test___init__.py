"""Tests for the dewey.core.automation.docs module."""

import logging
from typing import Any, Dict
from unittest.mock import patch

import pytest

from dewey.core.automation.docs import DocsModule
from dewey.core.script import BaseScript


class TestDocsModule:
    """Tests for the DocsModule class."""

    def test_docs_module_initialization_without_config(
        self, mock_base_script: Any
    ) -> None:
        """Tests DocsModule initialization without a config."""
        with patch("dewey.core.automation.docs.BaseScript.__init__") as mock_init:
            docs_module = DocsModule()
            assert docs_module.config is None
            mock_init.assert_called_once_with(None)

    def test_docs_module_initialization_with_config(
        self, mock_base_script: Any, mock_config: Dict[str, Any]
    ) -> None:
        """Tests DocsModule initialization with a config."""
        with patch("dewey.core.automation.docs.BaseScript.__init__") as mock_init:
            docs_module = DocsModule(config=mock_config)
            assert docs_module.config == mock_config
            mock_init.assert_called_once_with(mock_config)

    def test_run_method_logs_info_message(
        self, docs_module: DocsModule, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Tests that the run method logs an info message."""
        caplog.set_level(logging.INFO)
        docs_module.run()
        assert "Running the Docs module..." in caplog.text

    def test_get_config_value_returns_value_if_key_exists(
        self, docs_module: DocsModule, mock_config: Dict[str, Any]
    ) -> None:
        """Tests that get_config_value returns the correct value when the key exists."""
        docs_module.config = mock_config
        value = docs_module.get_config_value("key")
        assert value == "value"

    def test_get_config_value_returns_default_if_key_does_not_exist(
        self, docs_module: DocsModule
    ) -> None:
        """Tests that get_config_value returns the default value when the key does not exist."""
        docs_module.config = {}
        default_value = "default"
        value = docs_module.get_config_value("nonexistent_key", default_value)
        assert value == default_value

    def test_get_config_value_inherits_from_base_script(
        self, docs_module: DocsModule
    ) -> None:
        """Tests that get_config_value calls the superclass method."""
        with patch.object(
            BaseScript, "get_config_value", return_value="base_value"
        ) as mock_get_config_value:
            value = docs_module.get_config_value("key", "default")
            assert value == "base_value"
            mock_get_config_value.assert_called_once_with("key", "default")

    def test_run_method_can_be_overridden(
        self, docs_module: DocsModule, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Tests that the run method can be overridden in subclasses."""

        class CustomDocsModule(DocsModule):
            """Custom DocsModule class with overridden run method."""

            def run(self) -> None:
                """Overrides the run method to log a custom message."""
                self.logger.info("Custom run method")

        caplog.set_level(logging.INFO)
        custom_module = CustomDocsModule()
        custom_module.run()
        assert "Custom run method" in caplog.text
        assert "Running the Docs module..." not in caplog.text

    def test_docs_module_with_empty_config(
        self, mock_base_script: Any
    ) -> None:
        """Tests DocsModule initialization with an empty config."""
        with patch("dewey.core.automation.docs.BaseScript.__init__") as mock_init:
            docs_module = DocsModule(config={})
            assert docs_module.config == {}
            mock_init.assert_called_once_with({})

    def test_docs_module_with_none_config(
        self, mock_base_script: Any
    ) -> None:
        """Tests DocsModule initialization with a None config."""
        with patch("dewey.core.automation.docs.BaseScript.__init__") as mock_init:
            docs_module = DocsModule(config=None)
            assert docs_module.config is None
            mock_init.assert_called_once_with(None)

    def test_get_config_value_with_nested_key(
        self, docs_module: DocsModule, mock_config: Dict[str, Any]
    ) -> None:
        """Tests that get_config_value returns the correct value for a nested key."""
        docs_module.config = {"nested": {"key": "nested_value"}}
        value = docs_module.get_config_value("nested.key")
        assert value == "nested_value"

    def test_get_config_value_with_missing_nested_key(
        self, docs_module: DocsModule
    ) -> None:
        """Tests that get_config_value returns the default value for a missing nested key."""
        docs_module.config = {"nested": {}}
        default_value = "default"
        value = docs_module.get_config_value("nested.missing_key", default_value)
        assert value == default_value

    def test_get_config_value_with_empty_key(self, docs_module: DocsModule) -> None:
        """Tests that get_config_value returns the default value when the key is empty."""
        docs_module.config = {"key": "value"}
        default_value = "default"
        value = docs_module.get_config_value("", default_value)
        assert value == default_value

    def test_get_config_value_with_none_key(self, docs_module: DocsModule) -> None:
        """Tests that get_config_value returns the default value when the key is None."""
        docs_module.config = {"key": "value"}
        default_value = "default"
        value = docs_module.get_config_value(None, default_value)  # type: ignore
        assert value == default_value
