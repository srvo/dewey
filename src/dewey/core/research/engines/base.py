import argparse
from abc import abstractmethod
from typing import Any

from dewey.core.base_script import BaseScript


class BaseEngine(BaseScript):
    """
    Base class for all engines.

    This class provides a foundation for building engines within
    the Dewey project, offering standardized configuration,
    logging, and database/LLM integration.
    """

    def __init__(self, config_section: str = "base_engine") -> None:
        """
        Initializes the BaseEngine.

        Args:
        ----
            config_section: The configuration section to use for this engine.

        """
        super().__init__(
            config_section=config_section, requires_db=False, enable_llm=False,
        )
        self.logger.debug(
            "BaseEngine initialized with config section: %s", config_section,
        )

    @abstractmethod
    def execute(self) -> None:
        """
        Executes the engine's main logic.

        This method must be overridden by subclasses to implement the
        engine's specific functionality.

        Raises
        ------
            NotImplementedError: If the method is not implemented in a subclass.

        """
        raise NotImplementedError("Subclasses must implement the execute method.")

    def run(self) -> None:
        """Legacy method that calls execute() for backward compatibility."""
        self.logger.warning(
            "Using deprecated run() method. Update to use execute() instead.",
        )
        self.execute()

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Gets a configuration value for this engine.

        Args:
        ----
            key: The key of the configuration value to retrieve.
            default: The default value to return if the key is not found.

        Returns:
        -------
            The configuration value, or the default value if the key is not found.

        """
        return super().get_config_value(key, default)

    def info(self, message: str) -> None:
        """
        Logs an info message using the engine's logger.

        Args:
        ----
            message: The message to log.

        """
        self.logger.info(message)

    def error(self, message: str) -> None:
        """
        Logs an error message using the engine's logger.

        Args:
        ----
            message: The message to log.

        """
        self.error(message)

    def debug(self, message: str) -> None:
        """
        Logs a debug message using the engine's logger.

        Args:
        ----
            message: The message to log.

        """
        self.logger.debug(message)

    def warning(self, message: str) -> None:
        """
        Logs a warning message using the engine's logger.

        Args:
        ----
            message: The message to log.

        """
        self.logger.warning(message)

    def setup_argparse(self) -> argparse.ArgumentParser:
        """
        Set up command line arguments.

        Returns
        -------
            An argument parser configured with common options.

        """
        parser = super().setup_argparse()
        parser.add_argument(
            "--engine-config",
            help="Path to engine configuration file (overrides default config)",
        )
        return parser

    def parse_args(self) -> argparse.Namespace:
        """
        Parse command line arguments.

        Returns
        -------
            Parsed arguments

        """
        args = super().parse_args()

        # Update config if specified
        if hasattr(args, "engine_config") and args.engine_config:
            config_path = self.get_path(args.engine_config)
            if not config_path.exists():
                self.logger.error("Configuration file not found: %s", config_path)
                raise FileNotFoundError(
                    "Configuration file not found: %s" % config_path,
                )

            self.config = self._load_config()  # Reload the entire config
            self.logger.info("Loaded configuration from %s", config_path)

        return args
