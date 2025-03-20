from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

from dewey.core.automation import BaseScript
from dewey.core.db.connection import DatabaseConnection


class LLMClientInterface(ABC):
    """
    An interface for LLM clients, to enable mocking.
    """
    @abstractmethod
    def generate_text(self, prompt: str) -> str:
        pass


class FormFillingModule(BaseScript):
    """
    A module for managing form-filling automation tasks within Dewey.

    This module inherits from BaseScript and provides a standardized
    structure for form-filling scripts, including configuration
    loading, logging, and a `run` method to execute the script's
    primary logic.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initializes the FormFillingModule.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(*args, config_section="form_filling", requires_db=True, enable_llm=True, **kwargs)

    def run(
        self,
        generate_text_func: Optional[Callable[[Any, str], str]] = None,
        db_conn: Optional[DatabaseConnection] = None,
    ) -> None:
        """
        Executes the primary logic of the form-filling module.

        This method should be overridden in subclasses to implement the
        specific form-filling automation logic.

        Args:
            generate_text_func: A callable that takes an LLM client and a prompt,
                and returns generated text.  Defaults to `generate_text` if None.
            db_conn:  An optional database connection to use.  Defaults to
                `self.db_conn` if None.

        Returns:
            None

        Raises:
            Exception: If there is an error during form filling.
        """
        self.logger.info("Starting form filling module...")

        try:
            # Example of accessing a configuration value
            example_config_value = self.get_config_value("example_config_key", "default_value")
            self.logger.debug(f"Example config value: {example_config_value}")

            # Use provided db_conn or fall back to self.db_conn
            database_connection = db_conn or self.db_conn

            # Example of using the database connection
            if database_connection:
                result = database_connection.execute("SELECT 1;")  # Example query
                self.logger.debug(f"Database query result: {result}")

            # Use provided generate_text_func or fall back to generate_text with self.llm_client
            if generate_text_func:
                prompt = "Write a short poem about form filling."
                response = generate_text_func(self.llm_client, prompt)
                self.logger.info(f"LLM response: {response}")

            # Add your form-filling logic here
            self.logger.info("Form filling module completed.")

        except Exception as e:
            self.logger.error(f"Error during form filling: {e}", exc_info=True)
            raise

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a configuration value associated with the given key.

        Args:
            key: The key of the configuration value to retrieve.
            default: The default value to return if the key is not found.

        Returns:
            The configuration value associated with the key, or the default
            value if the key is not found.
        """
        return super().get_config_value(key, default)

