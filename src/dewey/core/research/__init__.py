from typing import Any

from dewey.core.base_script import BaseScript


class ResearchScript(BaseScript):
    """A base class for research scripts within the Dewey framework.

    Inherits from BaseScript and provides a standardized structure
    for research-related tasks.
    """

    def __init__(self, config_section: str = "research_script", **kwargs: Any) -> None:
        """Initializes the ResearchScript.

        Args:
            config_section (str): Configuration section name.
            **kwargs (Any): Additional keyword arguments.

        """
        super().__init__(
            name=self.__class__.__name__, config_section=config_section, **kwargs
        )

    def execute(self) -> None:
        """Executes the core logic of the research script.

        This method should be overridden by subclasses to implement
        specific research tasks.

        Raises:
            NotImplementedError: If the method is not implemented in the subclass.

        """
        raise NotImplementedError("Subclasses must implement the execute method.")

    def example_method(self, input_data: str) -> str:
        """An example method demonstrating the use of logger and config.

        Args:
            input_data: Input string data.

        Returns:
            A processed string.

        """
        config_value = self.get_config_value("example_config_key")
        self.logger.info(f"Processing data: {input_data} with config: {config_value}")
        return f"Processed: {input_data} - {config_value}"

    def run(self) -> None:
        """Legacy method for backward compatibility.

        New scripts should implement execute() instead of run().
        This method will be deprecated in a future version.
        """
        self.logger.warning(
            "Using deprecated run() method. Update to use execute() instead."
        )
        try:
            self.logger.info(f"Starting execution of {self.name}")

            # Call execute method
            self.execute()

            self.logger.info(f"Successfully completed {self.name}")
        except Exception as e:
            self.logger.error(f"Error executing {self.name}: {e}", exc_info=True)
            raise
        finally:
            self._cleanup()
