"""Tests for dewey.core.bookkeeping.docs module."""

import logging
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.bookkeeping.docs import DocsModule, DocumentationTask


class TestDocsModule:
    """Test suite for the DocsModule class."""

    @patch("dewey.core.bookkeeping.docs.BaseScript.__init__", return_value=None)
    def test_docs_module_initialization(
        self, mock_base_init: MagicMock, mock_base_script: MagicMock
    ) -> None:
        """Test that DocsModule initializes correctly."""
        docs_module = DocsModule(name="TestDocs", description="Test Description")

        assert docs_module.name == "TestDocs"
        assert docs_module.description == "Test Description"
        assert docs_module._documentation_task is None
        mock_base_init.assert_called_once_with(
            name="TestDocs", description="Test Description", config_section="docs"
        )

    @patch("dewey.core.bookkeeping.docs.BaseScript.__init__", return_value=None)
    def test_docs_module_initialization_with_task(
        self,
        mock_base_init: MagicMock,
        mock_base_script: MagicMock,
        mock_documentation_task: MagicMock,
    ) -> None:
        """Test that DocsModule initializes correctly with a documentation task."""
        docs_module = DocsModule(
            name="TestDocs",
            description="Test Description",
            documentation_task=mock_documentation_task,
        )

        assert docs_module.name == "TestDocs"
        assert docs_module.description == "Test Description"
        assert docs_module._documentation_task == mock_documentation_task
        mock_base_init.assert_called_once_with(
            name="TestDocs", description="Test Description", config_section="docs"
        )

    @patch("dewey.core.bookkeeping.docs.BaseScript.get_config_value")
    @patch("dewey.core.bookkeeping.docs.BaseScript.logger")
    @patch("dewey.core.bookkeeping.docs.BaseScript.__init__", return_value=None)
    def test_run_method_no_task(
        self,
        mock_base_init: MagicMock,
        mock_logger: MagicMock,
        mock_get_config_value: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test the run method executes without errors when no task is provided."""
        caplog.set_level(logging.INFO)
        mock_get_config_value.return_value = "test_value"
        docs_module = DocsModule(name="TestDocs")
        docs_module.run()

        mock_logger.info.assert_any_call("Running the Docs module...")
        mock_get_config_value.assert_called_once_with("docs_setting", "default_value")
        mock_logger.info.assert_any_call("Example config value: test_value")
        mock_logger.info.assert_any_call("Documentation tasks completed.")

    @patch("dewey.core.bookkeeping.docs.BaseScript.logger")
    @patch("dewey.core.bookkeeping.docs.BaseScript.__init__", return_value=None)
    def test_run_method_with_task(
        self,
        mock_base_init: MagicMock,
        mock_logger: MagicMock,
        mock_documentation_task: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test the run method executes the documentation task."""
        caplog.set_level(logging.INFO)
        docs_module = DocsModule(
            name="TestDocs", documentation_task=mock_documentation_task
        )
        docs_module.run()

        mock_logger.info.assert_any_call("Running the Docs module...")
        mock_documentation_task.execute.assert_called_once()
        mock_logger.info.assert_any_call("Documentation tasks completed.")

    @patch("dewey.core.bookkeeping.docs.BaseScript.logger")
    @patch("dewey.core.bookkeeping.docs.BaseScript.__init__", return_value=None)
    def test_run_method_with_error(
        self,
        mock_base_init: MagicMock,
        mock_logger: MagicMock,
        mock_documentation_task: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test the run method handles errors correctly."""
        caplog.set_level(logging.ERROR)
        mock_documentation_task.execute.side_effect = ValueError("Task error")
        docs_module = DocsModule(
            name="TestDocs", documentation_task=mock_documentation_task
        )

        with pytest.raises(ValueError, match="Task error"):
            docs_module.run()

        mock_logger.info.assert_any_call("Running the Docs module...")
        mock_documentation_task.execute.assert_called_once()
        mock_logger.error.assert_called_with(
            "An error occurred during documentation: Task error", exc_info=True
        )

    @patch("dewey.core.bookkeeping.docs.BaseScript.__init__", return_value=None)
    def test_get_config_value_exists(
        self, mock_base_init: MagicMock, mock_base_script: MagicMock
    ) -> None:
        """Test that get_config_value returns the correct value when the key exists."""
        docs_module = DocsModule(name="TestDocs")
        docs_module.config = {"test_key": "test_value"}
        value = docs_module.get_config_value("test_key")
        assert value == "test_value"

    @patch("dewey.core.bookkeeping.docs.BaseScript.__init__", return_value=None)
    def test_get_config_value_does_not_exist_with_default(
        self, mock_base_init: MagicMock, mock_base_script: MagicMock
    ) -> None:
        """Test that get_config_value returns the default value when the key does not exist."""
        docs_module = DocsModule(name="TestDocs")
        docs_module.config = {}
        default_value = "default_value"
        value = docs_module.get_config_value("nonexistent_key", default_value)
        assert value == default_value

    @patch("dewey.core.bookkeeping.docs.BaseScript.__init__", return_value=None)
    def test_get_config_value_does_not_exist_without_default(
        self, mock_base_init: MagicMock, mock_base_script: MagicMock
    ) -> None:
        """Test that get_config_value returns None when the key does not exist and no default is provided."""
        docs_module = DocsModule(name="TestDocs")
        docs_module.config = {}
        value = docs_module.get_config_value("nonexistent_key")
        assert value is None

    @patch("dewey.core.bookkeeping.docs.BaseScript.__init__", return_value=None)
    def test_get_config_value_nested_key_exists(
        self, mock_base_init: MagicMock, mock_base_script: MagicMock
    ) -> None:
        """Test that get_config_value returns the correct value for a nested key."""
        docs_module = DocsModule(name="TestDocs")
        docs_module.config = {"nested": {"test_key": "test_value"}}
        value = docs_module.get_config_value("nested.test_key")
        assert value == "test_value"

    @patch("dewey.core.bookkeeping.docs.BaseScript.__init__", return_value=None)
    def test_get_config_value_nested_key_does_not_exist(
        self, mock_base_init: MagicMock, mock_base_script: MagicMock
    ) -> None:
        """Test that get_config_value returns the default value for a nested key that does not exist."""
        docs_module = DocsModule(name="TestDocs")
        docs_module.config = {"nested": {}}
        default_value = "default_value"
        value = docs_module.get_config_value("nested.nonexistent_key", default_value)
        assert value == default_value

    @patch("dewey.core.bookkeeping.docs.BaseScript.__init__", return_value=None)
    def test_get_config_value_intermediate_key_does_not_exist(
        self, mock_base_init: MagicMock, mock_base_script: MagicMock
    ) -> None:
        """Test that get_config_value returns the default value when an intermediate key in the path does not exist."""
        docs_module = DocsModule(name="TestDocs")
        docs_module.config = {}
        default_value = "default_value"
        value = docs_module.get_config_value("nonexistent.test_key", default_value)
        assert value == default_value

    @patch("dewey.core.bookkeeping.docs.BaseScript.__init__", return_value=None)
    def test_get_config_value_empty_key(
        self, mock_base_init: MagicMock, mock_base_script: MagicMock
    ) -> None:
        """Test that get_config_value returns the entire config when an empty key is provided."""
        docs_module = DocsModule(name="TestDocs")
        docs_module.config = {"test_key": "test_value"}
        value = docs_module.get_config_value("")
        assert value is None

    @patch("dewey.core.bookkeeping.docs.BaseScript.__init__", return_value=None)
    def test_get_config_value_config_is_none(
        self, mock_base_init: MagicMock, mock_base_script: MagicMock
    ) -> None:
        """Test that get_config_value handles the case where the config is None."""
        docs_module = DocsModule(name="TestDocs")
        docs_module.config = None  # type: ignore[assignment]
        default_value = "default_value"
        value = docs_module.get_config_value("test_key", default_value)
        assert value == default_value

    @patch("dewey.core.bookkeeping.docs.BaseScript.__init__", return_value=None)
    def test_get_config_value_config_value_is_none(
        self, mock_base_init: MagicMock, mock_base_script: MagicMock
    ) -> None:
        """Test that get_config_value handles the case where the config value is None."""
        docs_module = DocsModule(name="TestDocs")
        docs_module.config = {"test_key": None}
        value = docs_module.get_config_value("test_key")
        assert value is None
