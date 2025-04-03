from dewey.core.base_script import BaseScript


class ResearchEngines(BaseScript):
    """Base class for research engines within Dewey.

    This class provides a standardized structure for research engines,
    including configuration loading, logging, and a `run` method to
    execute the engine's primary logic.
    """

    def __init__(
        self,
        name: str | None = None,
        description: str | None = None,
        config_section: str | None = None,
        requires_db: bool = False,
        enable_llm: bool = False,
    ) -> None:
        """Initializes the ResearchEngines class.

        Args:
            name: The name of the research engine. Defaults to the class name.
            description: A brief description of the engine.
            config_section: The section in the dewey.yaml config file to use.
            requires_db: Whether the engine requires a database connection.
            enable_llm: Whether the engine requires an LLM client.

        """
        super().__init__(
            name=name,
            description=description,
            config_section=config_section,
            requires_db=requires_db,
            enable_llm=enable_llm,
        )

    def run(self) -> None:
        """Executes the primary logic of the research engine.

        This method retrieves the engine name from the configuration and logs
        it.  Subclasses should override this method to implement their specific
        engine logic.

        Args:
            None

        Returns:
            None

        Raises:
            Exception: If there is an error during execution.

        """
        self.logger.info("Running research engine...")
        try:
            engine_name = self.get_config_value("engine_name", "DefaultEngine")
            self.logger.info(f"Engine name: {engine_name}")
        except Exception as e:
            self.logger.error(f"Error during engine execution: {e}", exc_info=True)
            raise
