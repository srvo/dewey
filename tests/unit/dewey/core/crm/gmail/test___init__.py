import logging
from typing import Any
from unittest.mock import MagicMock

import pytest

from dewey.core.base_script import BaseScript
from dewey.core.crm.gmail import GmailModule


class TestGmailModule:
    """Tests for the GmailModule class."""

    @pytest.fixture
    def gmail_module(self, mocker: Any) -> GmailModule:
        """Fixture for creating a GmailModule instance with mocked dependencies."""
        mocker.patch.object(BaseScript, "__init__", return_value=None)
        module = GmailModule()
        module.logger = MagicMock(spec=logging.Logger)
        return module

    def test_init(self, mocker: Any) -> None:
        """Tests the __init__ method of GmailModule."""
        mocker.patch.object(BaseScript, "__init__", return_value=None)
        module = GmailModule()
        assert module.name == "GmailModule"
        assert module.description is None
        assert module.config is None
        assert module.db_conn is None
        assert module.llm_client is None

    def test_run(self, gmail_module: GmailModule) -> None:
        """Tests the run method of GmailModule."""
        gmail_module.run()
        gmail_module.logger.info.assert_called_with("Gmail module finished.")
        gmail_module.logger.info.assert_called_with("Gmail module started.")

    def test_get_config_value(self, gmail_module: GmailModule) -> None:
        """Tests the get_config_value method of GmailModule."""
        gmail_module.config = {"test_key": "test_value"}
        value = gmail_module.get_config_value("test_key")
        assert value == "test_value"
        assert gmail_module.get_config_value("nonexistent_key", "default_value") == "default_value"
        assert gmail_module.get_config_value("nested.key", "default_value") == "default_value"

        gmail_module.config = {"nested": {"key": "nested_value"}}
        value = gmail_module.get_config_value("nested.key")
        assert value == "nested_value"

    def test_run_exception(self, gmail_module: GmailModule, mocker: Any) -> None:
        """Tests the run method when an exception occurs."""
        gmail_module.logger = MagicMock(spec=logging.Logger)
        gmail_module.logger.info.side_effect = Exception("Test Exception")

        with pytest.raises(Exception, match="Test Exception"):
            gmail_module.run()

        gmail_module.logger.info.assert_called_once_with("Gmail module started.")

    def test_get_config_value_no_config(self, gmail_module: GmailModule) -> None:
        """Tests get_config_value when config is None."""
        gmail_module.config = None
        assert gmail_module.get_config_value("test_key", "default_value") == "default_value"

    def test_get_config_value_empty_config(self, gmail_module: GmailModule) -> None:
        """Tests get_config_value when config is an empty dictionary."""
        gmail_module.config = {}
        assert gmail_module.get_config_value("test_key", "default_value") == "default_value"

    def test_get_config_value_nested_default(self, gmail_module: GmailModule) -> None:
        """Tests get_config_value with nested keys and a default value."""
        gmail_module.config = {"level1": {"level2": "value"}}
        assert gmail_module.get_config_value("level1.level2", "default") == "value"
        assert gmail_module.get_config_value("level1.level3", "default") == "default"
        assert gmail_module.get_config_value("level4.level5", "default") == "default"

    def test_get_config_value_type_consistency(self, gmail_module: GmailModule) -> None:
        """Tests that get_config_value returns values with correct types."""
        gmail_module.config = {"int_value": 123, "bool_value": True, "float_value": 3.14}
        assert isinstance(gmail_module.get_config_value("int_value"), int)
        assert isinstance(gmail_module.get_config_value("bool_value"), bool)
        assert isinstance(gmail_module.get_config_value("float_value"), float)

    def test_get_config_value_none_default(self, gmail_module: GmailModule) -> None:
        """Tests get_config_value with None as the default value."""
        gmail_module.config = {}
        assert gmail_module.get_config_value("missing_key", None) is None

    def test_get_config_value_empty_string_default(self, gmail_module: GmailModule) -> None:
        """Tests get_config_value with an empty string as the default value."""
        gmail_module.config = {}
        assert gmail_module.get_config_value("missing_key", "") == ""

    def test_get_config_value_zero_default(self, gmail_module: GmailModule) -> None:
        """Tests get_config_value with zero as the default value."""
        gmail_module.config = {}
        assert gmail_module.get_config_value("missing_key", 0) == 0

    def test_get_config_value_false_default(self, gmail_module: GmailModule) -> None:
        """Tests get_config_value with False as the default value."""
        gmail_module.config = {}
        assert gmail_module.get_config_value("missing_key", False) is False
