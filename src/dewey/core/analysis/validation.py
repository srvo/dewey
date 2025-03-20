from typing import Any, Dict, Optional, Protocol
from abc import abstractmethod

from dewey.core.base_script import BaseScript
from dewey.core.db.connection import DatabaseConnection, get_connection
from dewey.llm import llm_utils


class LLMClientInterface(Protocol):
    """
    An interface for LLM clients, defining a call_llm method.
    """
    @abstractmethod
    def call_llm(self, prompt: str, data: Dict[str, Any]) -> Optional[str]:
        ...


class DatabaseConnectionInterface(Protocol):
    """
    An interface for database connections, defining necessary methods.
    """
    @abstractmethod
    def cursor(self) -> Any:  # Replace Any with a more specific type if needed
        ...

    @abstractmethod
    def close(self) -> None:
        ...


class Validation(BaseScript):
    """
    A class for performing validation tasks.

    Inherits from BaseScript and provides standardized access to
    configuration, logging, and other utilities.
    """

    def __init__(
        self,
        config_section: str = "validation",
        llm_client: Optional[LLMClientInterface] = None,
        db_conn: Optional[DatabaseConnectionInterface] = None,
    ) -> None:
        """
        Initializes the Validation class.

        Args:
            config_section: The configuration section to use.
        """
        super().__init__(
            name="ValidationScript",
            description="Performs data validation tasks.",
            config_section=config_section,
            requires_db=True,
            enable_llm=True,
        )
        self._llm_client: Optional[LLMClientInterface] = llm_client
        self._db_conn: Optional[DatabaseConnectionInterface] = db_conn

    @property
    def llm_client(self) -> Optional[LLMClientInterface]:
        return self._llm_client

    @llm_client.setter
    def llm_client(self, llm_client: Optional[LLMClientInterface]) -> None:
        self._llm_client = llm_client

    @property
    def db_conn(self) -> Optional[DatabaseConnectionInterface]:
        return self._db_conn

    @db_conn.setter
    def db_conn(self, db_conn: Optional[DatabaseConnectionInterface]) -> None:
        self._db_conn = db_conn

    def run(self) -> None:
        """
        Executes the main logic of the validation script.
        """
        self.logger.info("Starting validation process.")

        # Accessing configuration values
        example_config_value = self.get_config_value("utils.example_config", "default_value")
        self.logger.info(f"Example config value: {example_config_value}")

        # Add your validation logic here
        self.example_method({"example": "data"})
        self.logger.info("Validation process completed.")

    def example_method(self, data: Dict[str, Any]) -> bool:
        """
        An example method that performs a validation check.

        Args:
            data: A dictionary containing data to validate.

        Returns:
            True if the data is valid, False otherwise.

        Raises:
            ValueError: If the input data is not a dictionary.
            Exception: If an error occurs during validation.
        """
        try:
            # Add your validation logic here
            if not isinstance(data, dict):
                self.logger.error("Data is not a dictionary.")
                raise ValueError("Data must be a dictionary.")

            # Example LLM call
            prompt = "Is this data valid?"
            if self.llm_client:
                response: Optional[str] = self.llm_client.call_llm(prompt, data)
                self.logger.info(f"LLM Response: {response}")

            # Example database operation
            if self.db_conn:
                with self.db_conn.cursor() as cur:
                    cur.execute("SELECT 1;")
                    result = cur.fetchone()
                    self.logger.info(f"Database check: {result}")

            return True  # Placeholder for actual validation logic
        except ValueError as ve:
            self.logger.error(f"Invalid data format: {ve}")
            return False
        except Exception as e:
            self.logger.exception(f"An error occurred during validation: {e}")
            return False

    def execute(self) -> None:
        """
        Executes the validation script.
        """
        super().execute()

    def _initialize_llm_client(self) -> None:
        """Initializes the LLM client."""
        try:
            llm_config = self.config.get("llm", {})
            self.llm_client = llm_utils.get_llm_client(llm_config)
            self.logger.debug("LLM client initialized successfully")
        except ImportError as e:
            self.logger.error(f"Could not import LLM modules: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize LLM client: {e}")
            raise

    def _initialize_db_connection(self) -> None:
        """Initializes the database connection."""
        try:
            db_config = self.config.get("database", {})
            self.db_conn = get_connection(db_config)
            self.logger.debug("Database connection initialized successfully")
        except ImportError as e:
            self.logger.error(f"Could not import database modules: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize database connection: {e}")
            raise


if __name__ == "__main__":
    validation_script = Validation()
    validation_script.execute()
