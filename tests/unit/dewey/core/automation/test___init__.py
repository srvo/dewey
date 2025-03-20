import logging
from typing import Any
from unittest.mock import patch

import pytest

from dewey.core.automation import AutomationModule
from dewey.core.base_script import BaseScript


class TestAutomationModule:
    """Unit tests for the AutomationModule class."""

    @pytest.fixture
    def automation_module(self) -> AutomationModule:
        """Fixture to create an instance of AutomationModule."""
        return AutomationModule()

    def test_inheritance(self, automation_module: AutomationModule) -> None:
        """Test that AutomationModule inherits from BaseScript."""
        assert isinstance(automation_module, BaseScript)

    def test_init_default_config_section(
        self, automation_module: AutomationModule
    ) -> None:
        """Test that the default config section is 'automation'."""
        assert automation_module.config_section == "automation"

    def test_init_custom_config_section(self) -> None:
        """Test initializing with a custom config section."""
        module = AutomationModule(config_section="custom_section")
        assert module.config_section == "custom_section"

    @patch("dewey.core.automation.BaseScript.__init__")
    def test_init_calls_super_init(self, mock_super_init: Any) -> None:
        """Test that the __init__ method calls the superclass's __init__."""
        AutomationModule(config_section="test_section")
        mock_super_init.assert_called_once_with(config_section="test_section")

    @patch("dewey.core.automation.AutomationModule.get_config_value")
    @patch("dewey.core.automation.AutomationModule.logger")
    def test_run_method(
        self,
        mock_logger: Any,
        mock_get_config_value: Any,
        automation_module: AutomationModule,
    ) -> None:
        """Test the run method execution."""
        mock_get_config_value.return_value = "test_value"
        automation_module.run()

        mock_logger.info.assert_any_call("Automation module started.")
        mock_logger.info.assert_any_call("Automation module finished.")
        mock_logger.info.assert_any_call("Example config value: test_value")
        mock_get_config_value.assert_called_with("example_config_key", "default_value")

    @patch("dewey.core.automation.BaseScript.get_config_value")
    def test_get_config_value(
        self, mock_super_get_config_value: Any, automation_module: AutomationModule
    ) -> None:
        """Test the get_config_value method."""
        mock_super_get_config_value.return_value = "config_value"
        value = automation_module.get_config_value("test_key", "default_value")
        assert value == "config_value"
        mock_super_get_config_value.assert_called_once_with("test_key", "default_value")

    def test_get_config_value_no_default(
        self, automation_module: AutomationModule
    ) -> None:
        """Test get_config_value without a default value."""
        automation_module.config = {"test_key": "config_value"}
        value = automation_module.get_config_value("test_key")
        assert value == "config_value"

    def test_get_config_value_default_returned(
        self, automation_module: AutomationModule
    ) -> None:
        """Test get_config_value when the key is not found and a default is provided."""
        default_value = "default_value"
        value = automation_module.get_config_value("nonexistent_key", default_value)
        assert value == default_value

    def test_get_config_value_key_not_found(
        self, automation_module: AutomationModule
    ) -> None:
        """Test get_config_value when the key is not found and no default is provided."""
        automation_module.config = {}
        value = automation_module.get_config_value("nonexistent_key")
        assert value is None

    @patch("dewey.core.automation.AutomationModule.logger")
    def test_run_no_exception(
        self, mock_logger: Any, automation_module: AutomationModule
    ) -> None:
        """Test that the run method does not raise an exception."""
        try:
            automation_module.run()
        except Exception as e:
            assert False, f"run() raised an exception {e}"

        mock_logger.info.assert_any_call("Automation module started.")
        mock_logger.info.assert_any_call("Automation module finished.")

    @patch("dewey.core.automation.AutomationModule.get_config_value")
    @patch("dewey.core.automation.AutomationModule.logger")
    def test_run_config_value(
        self,
        mock_logger: Any,
        mock_get_config_value: Any,
        automation_module: AutomationModule,
    ) -> None:
        """Test that the run method retrieves and logs a config value."""
        mock_get_config_value.return_value = "test_config_value"
        automation_module.run()

        mock_get_config_value.assert_called_once_with(
            "example_config_key", "default_value"
        )
        mock_logger.info.assert_any_call("Example config value: test_config_value")
