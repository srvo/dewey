import logging
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.automation.forms.form_filling import FormFillingModule
from dewey.core.db.connection import DatabaseConnection
from dewey.llm.llm_utils import generate_text


class TestFormFillingModule:
    """Tests for the FormFillingModule class."""

    @pytest.fixture
    def mock_base_script(self) -> MagicMock:
        """Mocks the BaseScript class."""
        mock = MagicMock()
        mock.name = "MockBaseScript"
        mock.description = "Mock BaseScript for testing"
        mock.config_section = "test_section"
        mock.requires_db = False
        mock.enable_llm = False
        mock.logger = MagicMock()
        mock.config = {}
        mock.db_conn = None
        mock.llm_client = None
        return mock

    @pytest.fixture
    def form_filling_module(self, mock_base_script: MagicMock) -> FormFillingModule:
        """Fixture for creating a FormFillingModule instance with mocked dependencies."""
        with patch("dewey.core.automation.forms.form_filling.BaseScript", return_value=mock_base_script):
            module = FormFillingModule()
        return module

    def test_init(self, form_filling_module: FormFillingModule) -> None:
        """Tests the __init__ method of FormFillingModule."""
        assert form_filling_module.config_section == "form_filling"

    def test_run_success(self, form_filling_module: FormFillingModule) -> None:
        """Tests the run method of FormFillingModule with mocked dependencies."""
        form_filling_module.get_config_value = MagicMock(return_value="test_value")
        form_filling_module.db_conn = MagicMock()
        form_filling_module.llm_client = MagicMock()

        with patch("dewey.core.automation.forms.form_filling.generate_text") as mock_generate_text:
            mock_generate_text.return_value = "LLM response"
            form_filling_module.run()

        form_filling_module.logger.info.assert_called()
        form_filling_module.logger.debug.assert_called()
        mock_generate_text.assert_called()

    def test_run_exception(self, form_filling_module: FormFillingModule) -> None:
        """Tests the run method of FormFillingModule when an exception is raised."""
        form_filling_module.get_config_value = MagicMock(side_effect=Exception("Test exception"))

        with pytest.raises(Exception, match="Test exception"):
            form_filling_module.run()
        form_filling_module.logger.error.assert_called()

    def test_get_config_value(self, form_filling_module: FormFillingModule) -> None:
        """Tests the get_config_value method of FormFillingModule."""
        form_filling_module.config = {"test_key": "test_value"}
        value = form_filling_module.get_config_value("test_key")
        assert value == "test_value"

        default_value = form_filling_module.get_config_value("non_existent_key", "default_value")
        assert default_value == "default_value"

    def test_run_no_db_no_llm(self, form_filling_module: FormFillingModule) -> None:
        """Tests the run method when no database or LLM is enabled."""
        form_filling_module.db_conn = None
        form_filling_module.llm_client = None
        form_filling_module.get_config_value = MagicMock(return_value="test_value")

        form_filling_module.run()

        form_filling_module.logger.info.assert_called()
        form_filling_module.logger.debug.assert_called()

    def test_run_with_db_exception(self, form_filling_module: FormFillingModule) -> None:
        """Tests the run method when a database exception occurs."""
        form_filling_module.db_conn = MagicMock()
        form_filling_module.db_conn.cursor.side_effect = Exception("DB Error")

        with pytest.raises(Exception, match="DB Error"):
            form_filling_module.run()
        form_filling_module.logger.error.assert_called()

    def test_run_with_llm_exception(self, form_filling_module: FormFillingModule) -> None:
        """Tests the run method when an LLM exception occurs."""
        form_filling_module.llm_client = MagicMock()
        with patch("dewey.core.automation.forms.form_filling.generate_text", side_effect=Exception("LLM Error")):
            with pytest.raises(Exception, match="LLM Error"):
                form_filling_module.run()
        form_filling_module.logger.error.assert_called()

    def test_inheritance_from_basescript(self, form_filling_module: FormFillingModule) -> None:
        """Tests that FormFillingModule inherits correctly from BaseScript."""
        assert isinstance(form_filling_module, FormFillingModule)
        # Additional checks to ensure BaseScript attributes are accessible
        assert hasattr(form_filling_module, 'logger')
        assert hasattr(form_filling_module, 'config')

    def test_config_access(self, form_filling_module: FormFillingModule) -> None:
        """Tests accessing configuration values."""
        form_filling_module.config = {"level1": {"level2": "config_value"}}
        config_value = form_filling_module.get_config_value("level1.level2")
        assert config_value == "config_value"

        default_value = form_filling_module.get_config_value("level1.nonexistent", "default")
        assert default_value == "default"

    def test_logging_messages(self, form_filling_module: FormFillingModule) -> None:
        """Tests that logging messages are correctly called."""
        form_filling_module.run()
        form_filling_module.logger.info.assert_called()
        form_filling_module.logger.debug.assert_called()

    def test_config_section_override(self) -> None:
        """Tests overriding the config section."""
        mock_base_script = MagicMock()
        mock_base_script.name = "MockBaseScript"
        mock_base_script.description = "Mock BaseScript for testing"
        mock_base_script.config_section = "override_section"
        mock_base_script.requires_db = False
        mock_base_script.enable_llm = False
        mock_base_script.logger = MagicMock()
        mock_base_script.config = {}
        mock_base_script.db_conn = None
        mock_base_script.llm_client = None

        with patch("dewey.core.automation.forms.form_filling.BaseScript", return_value=mock_base_script):
            module = FormFillingModule()
        assert module.config_section == "form_filling"  # Ensure it's still "form_filling"

