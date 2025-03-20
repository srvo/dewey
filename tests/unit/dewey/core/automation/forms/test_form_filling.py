"""Tests for FormFillingModule."""

from typing import Any, Callable, Optional
from unittest.mock import MagicMock, patch

import pytest

from dewey.core.automation.forms.form_filling import (
    FormFillingModule,
    LLMClientInterface,
)
from dewey.core.db.connection import DatabaseConnection


class TestFormFillingModule:
    """Tests for the FormFillingModule class."""

    def test_init(self, mock_base_script: MagicMock) -> None:
        """Tests the __init__ method of FormFillingModule."""
        with patch(
            "dewey.core.automation.forms.form_filling.BaseScript",
            return_value=mock_base_script,
        ):
            module = FormFillingModule()
            assert module.config_section == "form_filling"
            assert module.requires_db is True
            assert module.enable_llm is True

    def test_run_success(
        self, mock_base_script: MagicMock, mock_db_connection: MagicMock, mock_llm_client: MagicMock
    ) -> None:
        """Tests the run method of FormFillingModule with mocked dependencies."""
        mock_base_script.db_conn = mock_db_connection
        mock_base_script.llm_client = mock_llm_client

        with patch(
            "dewey.core.automation.forms.form_filling.BaseScript",
            return_value=mock_base_script,
        ):
            module = FormFillingModule()
            module.run()

        mock_base_script.logger.info.assert_called()
        mock_base_script.logger.debug.assert_called()
        mock_llm_client.generate_text.assert_called()
        mock_db_connection.execute.assert_called()

    def test_run_exception(self, mock_base_script: MagicMock) -> None:
        """Tests the run method of FormFillingModule when an exception is raised."""
        mock_base_script.get_config_value.side_effect = Exception("Test exception")

        with patch(
            "dewey.core.automation.forms.form_filling.BaseScript",
            return_value=mock_base_script,
        ), pytest.raises(Exception, match="Test exception"):
            module = FormFillingModule()
            module.run()

        mock_base_script.logger.error.assert_called()

    def test_get_config_value(self, mock_base_script: MagicMock, mock_config: dict[str, Any]) -> None:
        """Tests the get_config_value method of FormFillingModule."""
        mock_base_script.config = mock_config
        with patch(
            "dewey.core.automation.forms.form_filling.BaseScript",
            return_value=mock_base_script,
        ):
            module = FormFillingModule()
            value = module.get_config_value("example_config_key")
            assert value == "test_config_value"

            default_value = module.get_config_value("non_existent_key", "default_value")
            assert default_value == "default_value"

    def test_run_no_db_no_llm(self, mock_base_script: MagicMock) -> None:
        """Tests the run method when no database or LLM is enabled."""
        mock_base_script.db_conn = None
        mock_base_script.llm_client = None

        with patch(
            "dewey.core.automation.forms.form_filling.BaseScript",
            return_value=mock_base_script,
        ):
            module = FormFillingModule()
            module.run()

        module.logger.info.assert_called()
        module.logger.debug.assert_called()

    def test_run_with_db_exception(
        self, mock_base_script: MagicMock, mock_db_connection: MagicMock
    ) -> None:
        """Tests the run method when a database exception occurs."""
        mock_base_script.db_conn = mock_db_connection
        mock_db_connection.execute.side_effect = Exception("DB Error")

        with patch(
            "dewey.core.automation.forms.form_filling.BaseScript",
            return_value=mock_base_script,
        ), pytest.raises(Exception, match="DB Error"):
            module = FormFillingModule()
            module.run()

        mock_base_script.logger.error.assert_called()

    def test_run_with_llm_exception(
        self, mock_base_script: MagicMock, mock_llm_client: MagicMock
    ) -> None:
        """Tests the run method when an LLM exception occurs."""
        mock_base_script.llm_client = mock_llm_client
        mock_llm_client.generate_text.side_effect = Exception("LLM Error")

        with patch(
            "dewey.core.automation.forms.form_filling.BaseScript",
            return_value=mock_base_script,
        ), pytest.raises(Exception, match="LLM Error"):
            module = FormFillingModule()
            module.run()

        mock_base_script.logger.error.assert_called()

    def test_inheritance_from_basescript(self, mock_base_script: MagicMock) -> None:
        """Tests that FormFillingModule inherits correctly from BaseScript."""
        with patch(
            "dewey.core.automation.forms.form_filling.BaseScript",
            return_value=mock_base_script,
        ):
            module = FormFillingModule()
            assert isinstance(module, FormFillingModule)
            # Additional checks to ensure BaseScript attributes are accessible
            assert hasattr(module, "logger")
            assert hasattr(module, "config")

    def test_config_access(self, mock_base_script: MagicMock) -> None:
        """Tests accessing configuration values."""
        mock_base_script.config = {"level1": {"level2": "config_value"}}
        with patch(
            "dewey.core.automation.forms.form_filling.BaseScript",
            return_value=mock_base_script,
        ):
            module = FormFillingModule()
            config_value = module.get_config_value("level1.level2")
            assert config_value == "config_value"

            default_value = module.get_config_value("level1.nonexistent", "default")
            assert default_value == "default"

    def test_logging_messages(self, mock_base_script: MagicMock) -> None:
        """Tests that logging messages are correctly called."""
        with patch(
            "dewey.core.automation.forms.form_filling.BaseScript",
            return_value=mock_base_script,
        ):
            module = FormFillingModule()
            module.run()
            module.logger.info.assert_called()
            module.logger.debug.assert_called()

    def test_config_section_override(self, mock_base_script: MagicMock) -> None:
        """Tests overriding the config section."""
        mock_base_script.config_section = "override_section"

        with patch(
            "dewey.core.automation.forms.form_filling.BaseScript",
            return_value=mock_base_script,
        ):
            module = FormFillingModule()
            assert module.config_section == "form_filling"  # Ensure it's still "form_filling"

    def test_run_db_and_llm_interaction(
        self, mock_base_script: MagicMock, mock_db_connection: MagicMock, mock_llm_client: MagicMock
    ) -> None:
        """Tests the interaction with both DB and LLM."""
        mock_base_script.db_conn = mock_db_connection
        mock_base_script.llm_client = mock_llm_client

        with patch(
            "dewey.core.automation.forms.form_filling.BaseScript",
            return_value=mock_base_script,
        ):
            module = FormFillingModule()
            module.run()

        mock_db_connection.execute.assert_called()
        mock_llm_client.generate_text.assert_called()
        mock_base_script.logger.debug.assert_called()
        mock_base_script.logger.info.assert_called()

    def test_get_config_value_no_key(self, mock_base_script: MagicMock) -> None:
        """Tests get_config_value with an empty key."""
        with patch(
            "dewey.core.automation.forms.form_filling.BaseScript",
            return_value=mock_base_script,
        ):
            module = FormFillingModule()
            default_value = module.get_config_value("", "default")
            assert default_value == "default"

    def test_run_with_provided_db_conn(
        self, mock_base_script: MagicMock, mock_db_connection: MagicMock, mock_llm_client: MagicMock
    ) -> None:
        """Tests the run method with a provided database connection."""
        mock_base_script.db_conn = MagicMock()  # Ensure it's different from provided
        mock_base_script.llm_client = mock_llm_client

        with patch(
            "dewey.core.automation.forms.form_filling.BaseScript",
            return_value=mock_base_script,
        ):
            module = FormFillingModule()
            module.run(db_conn=mock_db_connection)

        mock_db_connection.execute.assert_called()
        mock_base_script.db_conn.execute.assert_not_called()  # Ensure original is not used

    def test_run_with_provided_generate_text_func(
        self, mock_base_script: MagicMock, mock_db_connection: MagicMock, mock_llm_client: MagicMock
    ) -> None:
        """Tests the run method with a provided generate_text function."""
        mock_base_script.db_conn = mock_db_connection
        mock_base_script.llm_client = mock_llm_client
        generate_text_func = MagicMock(return_value="Custom LLM Response")

        with patch(
            "dewey.core.automation.forms.form_filling.BaseScript",
            return_value=mock_base_script,
        ):
            module = FormFillingModule()
            module.run(generate_text_func=generate_text_func)

        generate_text_func.assert_called()
        mock_llm_client.generate_text.assert_not_called()  # Ensure original is not used
        mock_base_script.logger.info.assert_called_with("LLM response: Custom LLM Response")

    def test_run_with_llm_client_interface(
        self, mock_base_script: MagicMock, mock_db_connection: MagicMock
    ) -> None:
        """Tests the run method with a custom LLM client implementing the interface."""

        class MockLLMClient(LLMClientInterface):
            def generate_text(self, prompt: str) -> str:
                return "Custom LLM Response from Interface"

        mock_llm_client_instance = MockLLMClient()
        mock_base_script.db_conn = mock_db_connection
        mock_base_script.llm_client = mock_llm_client_instance

        with patch(
            "dewey.core.automation.forms.form_filling.BaseScript",
            return_value=mock_base_script,
        ):
            module = FormFillingModule()
            module.run()

        mock_base_script.logger.info.assert_called_with(
            "LLM response: Custom LLM Response from Interface"
        )

    def test_run_with_llm_client_interface_exception(
        self, mock_base_script: MagicMock, mock_db_connection: MagicMock
    ) -> None:
        """Tests the run method with a custom LLM client implementing the interface, but raises an exception."""

        class MockLLMClient(LLMClientInterface):
            def generate_text(self, prompt: str) -> str:
                raise ValueError("LLM Client Interface Error")

        mock_llm_client_instance = MockLLMClient()
        mock_base_script.db_conn = mock_db_connection
        mock_base_script.llm_client = mock_llm_client_instance

        with patch(
            "dewey.core.automation.forms.form_filling.BaseScript",
            return_value=mock_base_script,
        ), pytest.raises(Exception, match="LLM Client Interface Error"):
            module = FormFillingModule()
            module.run()

        mock_base_script.logger.error.assert_called()

    def test_run_db_conn_none(self, mock_base_script: MagicMock, mock_llm_client: MagicMock) -> None:
        """Tests the run method when db_conn is explicitly None."""
        mock_base_script.db_conn = None
        mock_base_script.llm_client = mock_llm_client

        with patch(
            "dewey.core.automation.forms.form_filling.BaseScript",
            return_value=mock_base_script,
        ):
            module = FormFillingModule()
            module.run()

        mock_base_script.logger.debug.assert_not_called()  # No DB interaction

    def test_run_generate_text_func_none(
        self, mock_base_script: MagicMock, mock_db_connection: MagicMock
    ) -> None:
        """Tests the run method when generate_text_func is explicitly None."""
        mock_base_script.db_conn = mock_db_connection
        mock_base_script.llm_client = None

        with patch(
            "dewey.core.automation.forms.form_filling.BaseScript",
            return_value=mock_base_script,
        ):
            module = FormFillingModule()
            module.run()

        mock_base_script.logger.info.assert_called()
