import logging
import os
import sys
from pathlib import Path
from typing import Any

import yaml

from dewey.core.base_script import CONFIG_PATH, BaseScript

# For testing purposes
try:
    from dewey.core.db.connection import get_connection
except ImportError:
    # Mock function for testing when actual module is not available
    def get_connection(*args, **kwargs):
        pass

try:
    from dewey.llm.llm_utils import get_llm_client
except ImportError:
    # Mock function for testing when actual module is not available
    def get_llm_client(*args, **kwargs):
        pass

# Get PROJECT_ROOT from dewey.yaml instead of defining it directly
def get_project_root() -> Path:
    """Get the project root from dewey.yaml config."""
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
            project_root = config.get('core', {}).get('project_root')
            if project_root:
                return Path(project_root)
    except (FileNotFoundError, yaml.YAMLError):
        pass
    
    # Fallback to the parent directory of the current module
    return Path(os.path.abspath(os.path.dirname(__file__))).parent.parent.parent

# Define PROJECT_ROOT using the config
PROJECT_ROOT = get_project_root()


class LogManager(BaseScript):
    """Manages logging configuration, rotation, and analysis.

    Inherits from BaseScript to provide standardized access to configuration,
    logging, and other utilities.
    """

    def __init__(self, config_section: str = "log_manager") -> None:
        """Initializes the LogManager.

        Args:
            config_section: The configuration section to use for this script.
        """
        super().__init__(config_section=config_section)

    def run(self) -> None:
        """Executes the main logic of the LogManager.

        This method is intended to be overridden by subclasses to implement
        specific logging management tasks.
        """
        try:
            self.logger.info("LogManager is running.")
        except Exception as e:
            self.logger.error(f"Error in run method: {e}")

    def get_log_level(self) -> str:
        """Retrieves the log level from the configuration.

        Returns:
            The log level as a string (e.g., "INFO", "DEBUG").
        """
        try:
            log_level = self.get_config_value("log_level", default="INFO")
            return log_level if log_level is not None else "INFO"
        except Exception as e:
            self.logger.error(f"Error in get_log_level method: {e}")
            return "INFO"  # Provide a default value in case of error

    def get_log_file_path(self) -> str:
        """Retrieves the log file path from the configuration.

        Returns:
            The log file path as a string.
        """
        try:
            log_file_path = self.get_config_value("log_file_path", default="application.log")
            return log_file_path if log_file_path is not None else "application.log"
        except Exception as e:
            self.logger.error(f"Error in get_log_file_path method: {e}")
            return "application.log"  # Provide a default value in case of error

    def some_other_function(self, arg: Any) -> None:
        """Example function demonstrating config and logging.

        Args:
            arg: An example argument.
        """
        try:
            value = self.get_config_value("some_config_key", default="default_value")
            self.logger.info(f"Some value: {value}, Arg: {arg}")
        except Exception as e:
            self.logger.error(f"Error in some_other_function method: {e}")

    def get_path(self, path: str) -> Path:
        """Get a path relative to the project root.
        
        Args:
            path: Path relative to project root or absolute path
            
        Returns:
            Resolved Path object
        """
        if os.path.isabs(path):
            return Path(path)
        # Convert string to Path for the test patch to work
        if isinstance(PROJECT_ROOT, str):
            return Path(PROJECT_ROOT) / path
        return PROJECT_ROOT / path

    def parse_args(self):
        """Parse command line arguments.
        
        Customized version that handles DB and LLM args properly for testing.
        
        Returns:
            Parsed arguments
        """
        parser = self.setup_argparse()
        args = parser.parse_args()
        
        # Update log level if specified
        if args.log_level:
            log_level = getattr(logging, args.log_level)
            self.logger.setLevel(log_level)
            self.logger.debug(f"Log level set to {args.log_level}")
            
        # Update config if specified
        if args.config:
            config_path = Path(args.config)
            if not config_path.exists():
                self.logger.error(f"Configuration file not found: {config_path}")
                sys.exit(1)
                
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            self.logger.info(f"Loaded configuration from {config_path}")
            
        # Update database connection if specified
        if self.requires_db and hasattr(args, 'db_connection_string') and args.db_connection_string:
            get_connection({"connection_string": args.db_connection_string})
            self.logger.info("Using custom database connection")
            
        # Update LLM model if specified
        if self.enable_llm and hasattr(args, 'llm_model') and args.llm_model:
            get_llm_client({"model": args.llm_model})
            self.logger.info(f"Using custom LLM model: {args.llm_model}")
            
        return args


if __name__ == "__main__":
    log_manager = LogManager()
    log_manager.execute()
