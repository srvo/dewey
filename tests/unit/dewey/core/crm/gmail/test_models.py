import logging
from unittest.mock import MagicMock

import pytest

from dewey.core.base_script import BaseScript
from dewey.core.crm.gmail.models import GmailModel


class TestGmailModel:
    """Test suite for the GmailModel class."""

    @pytest.fixture
    def gmail_model(self) -> GmailModel:
        """Fixture to create a GmailModel instance for testing."""
        model = GmailModel()
        model.logger = MagicMock(spec=logging.Logger)  # type: ignore
        model.config = {"gmail_api_key": "test_api_key"}
        return model

    def test_initialization(self, gmail_model: GmailModel) -> None:
        """Test that the GmailModel is initialized correctly."""
        assert gmail_model.name == "GmailModel"
        assert gmail_model.description == "A base model for Gmail interactions."

    def test_run_method(self, gmail_model: GmailModel) -> None:
        """Test the run method of the GmailModel."""
        gmail_model.run()
        gmail_model.logger.info.assert_called()
        gmail_model.logger.debug.assert_called()

    def test_run_method_config_access(self, gmail_model: GmailModel) -> None:
        """Test that the run method accesses configuration values."""
        gmail_model.get_config_value = MagicMock(return_value="test_api_key")  # type: ignore
        gmail_model.run()
        gmail_model.get_config_value.assert_called_with(
            "gmail_api_key", default="default_key"
        )

    def test_some_method(self, gmail_model: GmailModel) -> None:
        """Test the some_method of the GmailModel."""
        arg1 = "test_string"
        arg2 = 123
        result = gmail_model.some_method(arg1, arg2)
        assert result == f"Result: {arg1} - {arg2}"
        gmail_model.logger.info.assert_called()

    def test_some_method_logging(self, gmail_model: GmailModel) -> None:
        """Test that some_method logs the correct information."""
        arg1 = "test_string"
        arg2 = 123
        gmail_model.some_method(arg1, arg2)
        gmail_model.logger.info.assert_called_with(
            f"Executing some_method with arg1={arg1}, arg2={arg2}"
        )

    def test_get_config_value_existing_key(self, gmail_model: GmailModel) -> None:
        """Test get_config_value method with an existing key."""
        gmail_model.config = {"level1": {"level2": "value"}}
        value = gmail_model.get_config_value("level1.level2")
        assert value == "value"

    def test_get_config_value_missing_key(self, gmail_model: GmailModel) -> None:
        """Test get_config_value method with a missing key."""
        gmail_model.config = {"level1": {"level2": "value"}}
        value = gmail_model.get_config_value("level1.level3", default="default_value")
        assert value == "default_value"

    def test_get_config_value_missing_level(self, gmail_model: GmailModel) -> None:
        """Test get_config_value method with a missing level in the key path."""
        gmail_model.config = {"level1": {"level2": "value"}}
        value = gmail_model.get_config_value("level3.level4", default="default_value")
        assert value == "default_value"

    def test_get_config_value_empty_config(self, gmail_model: GmailModel) -> None:
        """Test get_config_value method with an empty configuration."""
        gmail_model.config = {}
        value = gmail_model.get_config_value("level1.level2", default="default_value")
        assert value == "default_value"

    def test_base_script_inheritance(self, gmail_model: GmailModel) -> None:
        """Test that GmailModel inherits from BaseScript."""
        assert isinstance(gmail_model, BaseScript)
