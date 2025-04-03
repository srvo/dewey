from typing import Optional

from dewey.core.base_script import BaseScript
from dewey.core.db.connection import DatabaseConnection


class BookkeepingScript(BaseScript):
    """Base class for bookkeeping-related scripts.

    This class inherits from BaseScript and provides a common
    foundation for bookkeeping scripts, including configuration
    loading and database connection management.
    """

    def __init__(
        self,
        config_section: str = "bookkeeping",
        db_connection: DatabaseConnection | None = None,
    ) -> None:
        """Initializes the BookkeepingScript.

        Args:
            config_section: The configuration section
                to use from the dewey.yaml file. Defaults to 'bookkeeping'.
            db_connection: Optional DatabaseConnection instance for dependency injection.

        """
        super().__init__(
            name=self.__class__.__name__,
            description=self.__doc__,
            config_section=config_section,
            requires_db=True,
            enable_llm=False,
            db_connection=db_connection,
        )

    def execute(self) -> None:
        """Execute the bookkeeping script.

        This implementation satisfies the abstract method requirement from BaseScript
        and calls the run method which should be implemented by subclasses.
        """
        try:
            self.logger.info(f"Starting execution of {self.name}")
            self.run()
            self.logger.info(f"Successfully completed {self.name}")
        except Exception as e:
            self.logger.error(f"Error executing {self.name}: {e}", exc_info=True)
            raise

    def run(self) -> None:
        """Abstract method to be implemented by subclasses.

        This method contains the core logic of the bookkeeping script.

        Raises:
            NotImplementedError: If the subclass does not implement this method.

        """
        raise NotImplementedError("Subclasses must implement the run method.")
