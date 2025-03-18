import os
import logging
import yaml
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

def load_config() -> Dict[str, Any]:
    """Load configuration from dewey.yaml."""
    config_path = Path(os.getenv('DEWEY_DIR', os.path.expanduser('~/dewey'))) / 'config' / 'dewey.yaml'
    with open(config_path) as f:
        return yaml.safe_load(f)

def setup_logging(
    name: str,
    log_dir: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> logging.Logger:
    """Set up logging with configuration from dewey.yaml.
    
    Args:
        name: Name of the logger (typically __name__ or script name)
        log_dir: Optional override for log directory
        config: Optional override for config (for testing)
    
    Returns:
        Configured logger instance
    """
    if config is None:
        config = load_config()
    
    log_config = config.get('logging', {})
    
    # Set up base logger
    logger = logging.getLogger(name)
    logger.setLevel(log_config.get('level', 'INFO'))
    
    # Clear any existing handlers
    logger.handlers = []
    
    # Create formatter
    formatter = logging.Formatter(
        fmt=log_config.get('format', '%(asctime)s - %(levelname)s - %(name)s - %(message)s'),
        datefmt=log_config.get('datefmt', '%Y-%m-%d %H:%M:%S')
    )
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Add file handler if log_dir is provided
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Use daily log files
        log_file = log_dir / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def get_logger(name: str, log_dir: Optional[str] = None) -> logging.Logger:
    """Get or create a logger with the given name.
    
    This is the main entry point for getting a logger in the Dewey project.
    
    Args:
        name: Name of the logger (typically __name__ or script name)
        log_dir: Optional override for log directory
    
    Returns:
        Configured logger instance
    """
    return setup_logging(name, log_dir) 