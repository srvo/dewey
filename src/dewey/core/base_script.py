#!/usr/bin/env python3

"""Base script template incorporating all centralized configurations.

This module serves as a template for creating new scripts in the dewey project.
It includes all necessary configurations, logging setup, and utility functions.

Typical usage example:
    from dewey.core.base_script import BaseScript

    class MyScript(BaseScript):
        def run(self):
            self.logger.info("Running my script")
            # Your script logic here

    if __name__ == "__main__":
        MyScript().main()
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

from dewey.utils import get_logger
from dewey.llm.llm_utils import get_llm_client
from dewey.core.engines import MotherDuckEngine

class BaseScriptError(Exception):
    """Base exception class for script errors."""


class BaseScript:
    """Base class for dewey scripts with common functionality.
    
    This class provides common functionality used across dewey scripts including:
    - Centralized logging configuration
    - LLM client setup
    - Database connection management
    - Argument parsing
    - Error handling
    
    Attributes:
        name: The name of the script, used for logging
        description: A description of what the script does
        logger: Configured logger instance
        args: Parsed command line arguments
    """

    def __init__(self, name: Optional[str] = None, description: Optional[str] = None):
        """Initialize the base script.

        Args:
            name: The name of the script. If not provided, uses the class name
            description: A description of the script's purpose
        """
        self.name = name or self.__class__.__name__.lower()
        self.description = description
        
        # Set up logging
        log_dir = os.path.join(os.getenv('DEWEY_DIR', os.path.expanduser('~/dewey')), 'logs')
        self.logger = get_logger(self.name, log_dir)
        
        # Initialize other attributes
        self.args = None
        self._llm_client = None
        self._db_engine = None

    @property
    def llm_client(self) -> Any:
        """Get or create the LLM client.

        Returns:
            The configured LLM client instance
        """
        if self._llm_client is None:
            self._llm_client = get_llm_client()
        return self._llm_client

    @property
    def db_engine(self) -> MotherDuckEngine:
        """Get or create the database engine.

        Returns:
            The configured MotherDuck database engine instance
        """
        if self._db_engine is None:
            self._db_engine = MotherDuckEngine()
        return self._db_engine

    def setup_argparse(self) -> argparse.ArgumentParser:
        """Set up command line argument parsing.

        Override this method to add script-specific command line arguments.

        Returns:
            Configured argument parser instance
        """
        parser = argparse.ArgumentParser(
            description=self.description or f"Run the {self.name} script"
        )
        # Add common arguments here
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Enable debug logging"
        )
        return parser

    def validate_args(self, args: argparse.Namespace) -> None:
        """Validate command line arguments.

        Override this method to add script-specific argument validation.

        Args:
            args: Parsed command line arguments

        Raises:
            BaseScriptError: If argument validation fails
        """
        pass

    def initialize(self) -> None:
        """Initialize script resources.

        Override this method to add script-specific initialization.
        Called after argument parsing but before run().

        Raises:
            BaseScriptError: If initialization fails
        """
        pass

    def cleanup(self) -> None:
        """Clean up script resources.

        Override this method to add script-specific cleanup.
        Called after run() completes or fails.
        """
        if self._db_engine is not None:
            self._db_engine.close()

    def run(self) -> None:
        """Run the script.

        Override this method to implement script-specific logic.

        Raises:
            BaseScriptError: If script execution fails
        """
        raise NotImplementedError("Subclasses must implement run()")

    def main(self) -> None:
        """Main entry point for the script.

        Handles argument parsing, initialization, execution, and cleanup.
        """
        start_time = datetime.now()
        
        try:
            # Parse arguments
            parser = self.setup_argparse()
            self.args = parser.parse_args()
            
            # Configure debug logging if requested
            if self.args.debug:
                self.logger.setLevel("DEBUG")
            
            # Validate arguments
            self.validate_args(self.args)
            
            # Initialize
            self.logger.info(f"Starting {self.name}")
            self.initialize()
            
            # Run the script
            self.run()
            
            # Log completion
            duration = datetime.now() - start_time
            self.logger.info(f"Completed {self.name} in {duration}")
            
        except BaseScriptError as e:
            self.logger.error(str(e))
            sys.exit(1)
        except Exception as e:
            self.logger.exception(f"Unexpected error in {self.name}: {str(e)}")
            sys.exit(1)
        finally:
            self.cleanup()


class ExampleScript(BaseScript):
    """Example implementation of a script using BaseScript."""

    def __init__(self):
        """Initialize the example script."""
        super().__init__(
            name="example_script",
            description="Example script showing BaseScript usage"
        )

    def setup_argparse(self) -> argparse.ArgumentParser:
        """Set up argument parsing for the example script."""
        parser = super().setup_argparse()
        parser.add_argument(
            "--input-file",
            type=Path,
            help="Input file to process"
        )
        return parser

    def validate_args(self, args: argparse.Namespace) -> None:
        """Validate arguments for the example script."""
        if args.input_file and not args.input_file.exists():
            raise BaseScriptError(f"Input file not found: {args.input_file}")

    def initialize(self) -> None:
        """Initialize the example script."""
        self.logger.info("Initializing example script")
        # Example initialization code

    def run(self) -> None:
        """Run the example script."""
        self.logger.info("Running example script")
        
        # Example LLM usage
        response = self.llm_client.generate(
            prompt="What is 2+2?",
            max_tokens=10
        )
        self.logger.info(f"LLM response: {response}")
        
        # Example database usage
        result = self.db_engine.execute("SELECT 1")
        self.logger.info(f"Database result: {result}")


if __name__ == "__main__":
    # Example usage
    ExampleScript().main() 