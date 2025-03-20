import logging
from typing import Any
from unittest.mock import patch

import pytest

from dewey.core.automation.forms import FormsModule
from dewey.core.script import BaseScript


class TestFormsModule:
    """Tests for the FormsModule class."""

    @pytest.fixture
    def forms_module(self) -> FormsModule:
        """Fixture to create a FormsModule instance."""
        return FormsModule()

    def test_inheritance(self, forms_module: FormsModule) -> None:
        """Test that FormsModule inherits from BaseScript."""
        assert isinstance(forms_module, BaseScript)

    def test_init_with_config_section(self) -> None:
        """Test that FormsModule can be initialized with a config section."""
        module = FormsModule(config_section="test_section")
        assert module.config_section == "test_section"

    def test_run_method_no_exception(self, forms_module: FormsModule, caplog: pytest.LogCaptureFixture) -> None:
        """Test that the run method executes without raising an exception when no logic is present."""
        with caplog.at_level(logging.INFO):
            forms_module.run()
        assert "Forms module started." in caplog.text
        assert "Forms module finished." in caplog.text

    def test_run_method_exception_handling(self, forms_module: FormsModule, caplog: pytest.LogCaptureFixture) -> None:
        """Test that the run method handles exceptions and logs them."""
        with patch.object(FormsModule, "run", side_effect=ValueError("Test exception")):
            with pytest.raises(ValueError, match="Test exception"):
                forms_module.run()
            assert "An error occurred during form processing: Test exception" in caplog.text

    def test_get_config_value_existing_key(self, forms_module: FormsModule) -> None:
        """Test that get_config_value retrieves an existing configuration value."""
        forms_module.config = {"test_key": "test_value"}
        value = forms_module.get_config_value("test_key")
        assert value == "test_value"

    def test_get_config_value_default_value(self, forms_module: FormsModule) -> None:
        """Test that get_config_value returns the default value when the key is not found."""
        value = forms_module.get_config_value("non_existent_key", "default_value")
        assert value == "default_value"

    def test_get_config_value_no_default_value(self, forms_module: FormsModule) -> None:
        """Test that get_config_value returns None when the key is not found and no default value is provided."""
        value = forms_module.get_config_value("non_existent_key")
        assert value is None

    def test_run_method_accesses_config(self, forms_module: FormsModule, caplog: pytest.LogCaptureFixture) -> None:
        """Test that the run method can access configuration values."""
        forms_module.config = {"api_key": "test_api_key"}

        with patch.object(forms_module.logger, "info") as mock_info:
            forms_module.run()
            mock_info.assert_called_with("Forms module started.")

        with caplog.at_level(logging.INFO):
            forms_module.run()
        assert "Forms module started." in caplog.text
        assert "Forms module finished." in caplog.text
