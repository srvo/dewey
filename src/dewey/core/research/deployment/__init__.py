from typing import Any

from dewey.core.base_script import BaseScript


class DeploymentModule(BaseScript):
    """Base class for deployment modules within Dewey.

    This class provides a standardized structure for deployment scripts,
    including configuration loading, logging, and a `run` method to
    execute the script's primary logic.
    """

    def __init__(
        self,
        config_section: str = "deployment",
        requires_db: bool = False,
        enable_llm: bool = False,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initializes the DeploymentModule.

        Args:
            config_section (str): Section in dewey.yaml to load for this script. Defaults to "deployment".
            requires_db (bool): Whether this script requires database access. Defaults to False.
            enable_llm (bool): Whether this script requires LLM access. Defaults to False.
            *args (Any): Additional positional arguments.
            **kwargs (Any): Additional keyword arguments.

        """
        super().__init__(
            config_section=config_section,
            requires_db=requires_db,
            enable_llm=enable_llm,
            *args,
            **kwargs,
        )
        self.name = "DeploymentModule"
        self.description = "Base class for deployment modules."

    def execute(self) -> None:
        """Executes the deployment logic.

        This method should be overridden by subclasses to implement the
        specific deployment steps.

        Args:
            None

        Returns:
            None

        Raises:
            Exception: If an error occurs during deployment.

        """
        self.logger.info("Deployment module started.")
        try:
            # Add deployment logic here
            config_value = self.get_config_value("example_config_key", "default_value")
            self.logger.info(f"Example config value: {config_value}")

            # Example of using database connection
            if self.requires_db and self.db_conn:
                try:
                    cursor = self.db_conn.cursor()
                    cursor.execute("SELECT 1")  # Example query
                    result = cursor.fetchone()
                    self.logger.info(f"Database connection test: {result}")
                except Exception as db_error:
                    self.logger.error(f"Database error: {db_error}")

            # Example of using LLM client
            if self.enable_llm and self.llm_client:
                try:
                    response = self.llm_client.generate(
                        prompt="Write a short poem about deployment."
                    )
                    self.logger.info(f"LLM response: {response}")
                except Exception as llm_error:
                    self.logger.error(f"LLM error: {llm_error}")

        except Exception as e:
            self.logger.error(f"Deployment failed: {e}")
            raise
        finally:
            self.logger.info("Deployment module finished.")

    def run(self) -> None:
        """Legacy method that calls execute() for backward compatibility."""
        self.logger.warning(
            "Using deprecated run() method. Update to use execute() instead."
        )
        self.execute()
