from dewey.core.base_script import BaseScript
from typing import Optional


class AnalysisScript(BaseScript):
    """
    Base class for analysis scripts in the Dewey project.

    This class provides a standardized way to access configuration, logging,
    database connections, and LLM integrations. It inherits from BaseScript
    and implements the abstract run method.

    Attributes:
        name (str): Name of the script (used for logging).
        description (str): Description of the script.
        logger (logging.Logger): Configured logger instance.
        config (Dict[str, Any]): Loaded configuration from dewey.yaml.
        db_conn (DatabaseConnection): Database connection (if enabled).
        llm_client: LLM client (if enabled).
    """

    def __init__(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        config_section: Optional[str] = None,
        requires_db: bool = False,
        enable_llm: bool = False,
    ) -> None:
        """
        Initialize the AnalysisScript.

        Args:
            name (Optional[str]): Name of the script (used for logging).
                Defaults to the class name.
            description (Optional[str]): Description of the script.
                Defaults to None.
            config_section (Optional[str]): Section in dewey.yaml to load
                for this script. Defaults to None.
            requires_db (bool): Whether this script requires database access.
                Defaults to False.
            enable_llm (bool): Whether this script requires LLM access.
                Defaults to False.
        """
        super().__init__(
            name=name,
            description=description,
            config_section=config_section,
            requires_db=requires_db,
            enable_llm=enable_llm,
        )

    def run(self) -> None:
        """
        Abstract method to be implemented by subclasses.

        This method contains the core logic of the analysis script.
        """
        raise NotImplementedError("Subclasses must implement the run method.")


if __name__ == "__main__":
    # Example usage (replace with your actual script logic)
    class MyAnalysisScript(AnalysisScript):
        """
        Example analysis script.
        """

        def __init__(self):
            """Function __init__."""
            super().__init__(
                name="MyAnalysisScript",
                description="An example analysis script",
                config_section="my_analysis",
                requires_db=True,
                enable_llm=True,
            )

        def run(self) -> None:
            """
            Run the example analysis script.
            """
            self.logger.info("Running MyAnalysisScript")
            # Access configuration values
            example_value = self.get_config_value("example_key", "default_value")
            self.logger.info(f"Example config value: {example_value}")

            # Access database connection
            if self.db_conn:
                try:
                    cursor = self.db_conn.cursor()
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    self.logger.info(f"Database connection test: {result}")
                except Exception as e:
                    self.logger.error(f"Error accessing database: {e}")
                finally:
                    cursor.close()

            # Access LLM client
            if self.llm_client:
                try:
                    response = self.llm_client.generate(prompt="Hello, LLM!")
                    self.logger.info(f"LLM response: {response}")
                except Exception as e:
                    self.logger.error(f"Error accessing LLM: {e}")

    # Create and execute the script
    script = MyAnalysisScript()
    script.execute()
