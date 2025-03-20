import logging
from typing import Any, Dict, Optional
from unittest.mock import patch

import pytest

from dewey.core.automation.docs import DocsModule
from dewey.core.script import BaseScript


class TestDocsModule:
    """Tests for the DocsModule class."""

    @pytest.fixture
    def mock_base_script(self) -> None:
        """Mocks the BaseScript class."""
        with patch("dewey.core.automation.docs.BaseScript.__init__") as mock:
            yield mock

    @pytest.fixture
    def docs_module(self, mock_base_script: Any) -> DocsModule:
        """Fixture for creating a DocsModule instance."""
        mock_base_script.return_value = None  # type: ignore
        return DocsModule()

    def test_docs_module_initialization_without_config(
        self, mock_base_script: Any
    ) -> None:
        """Tests DocsModule initialization without a config."""
        docs_module = DocsModule()
        assert docs_module.config is None
        mock_base_script.assert_called_once_with(None)

    def test_docs_module_initialization_with_config(
        self, mock_base_script: Any
    ) -> None:
        """Tests DocsModule initialization with a config."""
        config: Dict[str, Any] = {"key": "value"}
        docs_module = DocsModule(config=config)
        assert docs_module.config == config
        mock_base_script.assert_called_once_with(config)

    def test_run_method_logs_info_message(
        self, docs_module: DocsModule, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Tests that the run method logs an info message."""
        caplog.set_level(logging.INFO)
        docs_module.run()
        assert "Running the Docs module..." in caplog.text

    def test_get_config_value_returns_value_if_key_exists(
        self, docs_module: DocsModule
    ) -> None:
        """Tests that get_config_value returns the correct value when the key exists."""
        config: Dict[str, Any] = {"key": "value"}
        docs_module.config = config
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
            def run(self) -> None:
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
        docs_module = DocsModule(config={})
        assert docs_module.config == {}
        mock_base_script.assert_called_once_with({})

    def test_docs_module_with_none_config(
        self, mock_base_script: Any
    ) -> None:
        """Tests DocsModule initialization with a None config."""
        docs_module = DocsModule(config=None)
        assert docs_module.config is None
        mock_base_script.assert_called_once_with(None)
