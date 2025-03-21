"""Base class for all Dewey scripts.

This module implements the BaseScript class, which serves as the foundation
for all scripts in the Dewey project. It provides standardized access to:
- Configuration management (via dewey.yaml)
- Logging facilities
- Database connections
- LLM integrations
- Error handling

All non-test scripts MUST inherit from this class as specified in the 
project conventions.
"""

import argparse
import logging
import os
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, cast

import yaml
from dotenv import load_dotenv

# Set path to project root to ensure consistent config loading
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "dewey.yaml"


class BaseScript(ABC):
    """Base class for all Dewey scripts.
    
    This class provides standardized access to configuration, logging,
    database connections, and LLM integrations.
    
    Attributes:
        name: Name of the script (used for logging)
        description: Description of the script
        logger: Configured logger instance
        config: Loaded configuration from dewey.yaml
        db_conn: Database connection (if enabled)
        llm_client: LLM client (if enabled)
    """

    def __init__(
        self, 
        name: Optional[str] = None, 
        description: Optional[str] = None,
        config_section: Optional[str] = None,
        requires_db: bool = False,
        enable_llm: bool = False,
    ) -> None:
        """Initialize base script functionality.
        
        Args:
            name: Name of the script (used for logging)
            description: Description of the script
            config_section: Section in dewey.yaml to load for this script
            requires_db: Whether this script requires database access
            enable_llm: Whether this script requires LLM access
        """
        # Load environment variables
        load_dotenv(PROJECT_ROOT / ".env")
        
        # Set basic attributes
        self.name = name or self.__class__.__name__
        self.description = description
        self.config_section = config_section
        self.requires_db = requires_db
        self.enable_llm = enable_llm
        
        # Setup logging before anything else
        self._setup_logging()
        
        # Load configuration
        self.config = self._load_config()
        
        # Initialize database connection if required
        self.db_conn = None
        if self.requires_db:
            self._initialize_db_connection()
            
        # Initialize LLM client if required
        self.llm_client = None
        if self.enable_llm:
            self._initialize_llm_client()
            
        self.logger.info(f"Initialized {self.name}")

    def _setup_logging(self) -> None:
        """Set up logging for this script."""
        # Configure logging format from config if available
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = yaml.safe_load(f)
                log_config = config.get('core', {}).get('logging', {})
                log_level = getattr(logging, log_config.get('level', 'INFO'))
                log_format = log_config.get(
                    'format', 
                    '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
                )
                date_format = log_config.get('date_format', '%Y-%m-%d %H:%M:%S')
        except Exception as e:
            # Default logging configuration if config can't be loaded
            log_level = logging.INFO
            log_format = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
            date_format = '%Y-%m-%d %H:%M:%S'
        
        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format=log_format,
            datefmt=date_format,
        )
        
        # Get logger for this script
        self.logger = logging.getLogger(self.name)

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from dewey.yaml.
        
        Returns:
            Dictionary containing configuration
        
        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            yaml.YAMLError: If the configuration file isn't valid YAML
        """
        try:
            self.logger.debug(f"Loading configuration from {CONFIG_PATH}")
            with open(CONFIG_PATH, 'r') as f:
                all_config = yaml.safe_load(f)
                
            # Load specific section if requested
            if self.config_section:
                if self.config_section not in all_config:
                    self.logger.warning(
                        f"Config section '{self.config_section}' not found in dewey.yaml. "
                        "Using full config."
                    )
                    return all_config
                return all_config[self.config_section]
            
            return all_config
        except FileNotFoundError:
            self.logger.error(f"Configuration file not found: {CONFIG_PATH}")
            raise
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing YAML configuration: {e}")
            raise

    def _initialize_db_connection(self) -> None:
        """Initialize database connection if required."""
        try:
            from dewey.core.db.connection import get_connection
            
            self.logger.debug("Initializing database connection")
            db_config = self.config.get('core', {}).get('database', {})
            self.db_conn = get_connection(db_config)
            self.logger.debug("Database connection established")
        except ImportError:
            self.logger.error("Could not import database module. Is it installed?")
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize database connection: {e}")
            raise

    def _initialize_llm_client(self) -> None:
        """Initialize LLM client if required."""
        try:
            from dewey.llm.litellm_client import LiteLLMClient, LiteLLMConfig
            
            self.logger.debug("Initializing LLM client")
            llm_config = self.config.get('llm', {})
            config = LiteLLMConfig(**llm_config)
            self.llm_client = LiteLLMClient(config=config)
            self.logger.debug("LLM client initialized")
        except ImportError:
            self.logger.error("Could not import LLM module. Is it installed?")
            # Don't raise to allow scripts to run without LLM support
            self.llm_client = None 
        except Exception as e:
            self.logger.error(f"Failed to initialize LLM client: {e}")
            self.llm_client = None

    def setup_argparse(self) -> argparse.ArgumentParser:
        """Set up command line arguments.
        
        Returns:
            An argument parser configured with common options.
        """
        parser = argparse.ArgumentParser(description=self.description)
        parser.add_argument(
            "--config", 
            help=f"Path to configuration file (default: {CONFIG_PATH})"
        )
        parser.add_argument(
            "--log-level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            help="Set logging level"
        )
        
        # Add database-specific arguments if needed
        if self.requires_db:
            parser.add_argument(
                "--db-connection-string",
                help="Database connection string (overrides config)"
            )
        
        # Add LLM-specific arguments if needed
        if self.enable_llm:
            parser.add_argument(
                "--llm-model",
                help="LLM model to use (overrides config)"
            )
            
        return parser

    def parse_args(self) -> argparse.Namespace:
        """Parse command line arguments.
        
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
            from dewey.core.db.connection import get_connection
            self.db_conn = get_connection({"connection_string": args.db_connection_string})
            self.logger.info("Using custom database connection")
            
        # Update LLM model if specified
        if self.enable_llm and hasattr(args, 'llm_model') and args.llm_model:
            from dewey.llm.litellm_client import LiteLLMClient, LiteLLMConfig
            self.llm_client = LiteLLMClient(config=LiteLLMConfig(model=args.llm_model))
            self.logger.info(f"Using custom LLM model: {args.llm_model}")
            
        return args

    @abstractmethod
    def run(self) -> None:
        """Run the script.
        
        This method must be implemented by all subclasses.
        """
        pass

    def execute(self) -> None:
        """Execute the script.
        
        This method handles the common setup and execution flow:
        1. Parse arguments
        2. Set up logging and configuration
        3. Run the script
        4. Handle exceptions
        5. Clean up resources
        """
        try:
            # Parse arguments
            args = self.parse_args()
            
            # Run the script
            self.logger.info(f"Starting execution of {self.name}")
            self.run()
            self.logger.info(f"Completed execution of {self.name}")
            
        except KeyboardInterrupt:
            self.logger.warning("Script interrupted by user")
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"Error executing script: {e}", exc_info=True)
            sys.exit(1)
        finally:
            # Clean up resources
            self._cleanup()

    def _cleanup(self) -> None:
        """Clean up resources."""
        # Close database connection if open
        if self.db_conn is not None:
            try:
                self.logger.debug("Closing database connection")
                self.db_conn.close()
            except Exception as e:
                self.logger.warning(f"Error closing database connection: {e}")

    def get_path(self, path: Union[str, Path]) -> Path:
        """Get a path relative to the project root.
        
        Args:
            path: Path relative to project root or absolute path
            
        Returns:
            Resolved Path object
        """
        if os.path.isabs(path):
            return Path(path)
        return PROJECT_ROOT / path
        
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a value from the configuration.
        
        Args:
            key: Dot-separated path to the configuration value (e.g., "llm.model")
            default: Default value to return if the key doesn't exist
            
        Returns:
            Configuration value or default
        """
        if not key:
            return default
            
        parts = key.split('.')
        config = self.config
        
        for part in parts:
            # Handle empty part (e.g., "level1.")
            if part == "":
                return default
                
            if isinstance(config, dict) and part in config:
                config = config[part]
            else:
                return default
                
        return config