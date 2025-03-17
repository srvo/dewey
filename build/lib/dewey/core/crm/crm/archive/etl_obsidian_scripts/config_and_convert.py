#!/usr/bin/env python3
"""
Configuration and Conversion Script

This script helps convert existing Python scripts to our standardized pattern.
It sets up the proper directory structure, logging, and package configuration.
"""
import os
import shutil
from pathlib import Path
import logging
import sys
import subprocess
from typing import Optional, Dict, Any
import json
import yaml

class ScriptConverter:
    """Converts existing scripts to our standardized pattern."""

    def __init__(self, script_name: str, script_path: str):
        self.script_name = script_name
        self.source_path = Path(script_path)
        self.workspace_dir = Path(os.path.expanduser('~')) / "Library/Mobile Documents/iCloud~md~obsidian/Documents/dev"
        self.target_dir = self.workspace_dir / "scripts" / script_name
        self.setup_logging()

    def setup_logging(self):
        """Set up basic logging for the converter."""
        self.logger = logging.getLogger(__name__)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def create_directory_structure(self):
        """Create the standardized directory structure."""
        self.logger.info(f"Creating directory structure for {self.script_name}")
        
        # Create main directories
        package_dir = self.target_dir / self.script_name
        test_dir = self.target_dir / "tests"
        
        os.makedirs(package_dir, exist_ok=True)
        os.makedirs(test_dir, exist_ok=True)
        
        # Create package files
        self._create_file(package_dir / "__init__.py", self._get_init_template())
        self._create_file(package_dir / "__main__.py", self._get_main_template())
        self._create_file(package_dir / "core.py", self._get_core_template())
        self._create_file(package_dir / "config.py", self._get_config_template())
        self._create_file(package_dir / "log_handler.py", self._get_log_handler_template())
        
        # Create test files
        self._create_file(test_dir / "__init__.py", "")
        self._create_file(test_dir / f"test_{self.script_name}.py", self._get_test_template())
        
        # Create root files
        self._create_file(self.target_dir / "run.py", self._get_run_template())
        self._create_file(self.target_dir / "README.md", self._get_readme_template())
        self._create_file(self.target_dir / "pyproject.toml", self._get_pyproject_template())

    def setup_poetry(self):
        """Initialize poetry and install dependencies."""
        self.logger.info("Setting up Poetry project")
        os.chdir(self.target_dir)
        
        try:
            # Initialize git if not already initialized
            if not (self.target_dir / ".git").exists():
                subprocess.run(["git", "init"], check=True)
            
            # Install dependencies
            subprocess.run([
                "poetry", "add",
                "python-dotenv",  # Environment management
                "pyyaml",         # Configuration
                "psutil",         # Resource monitoring
                "tqdm",          # Progress bars
            ], check=True)
            
            # Install dev dependencies
            subprocess.run([
                "poetry", "add", "--group", "dev",
                "pytest",
                "pytest-cov",
                "black",
                "flake8",
                "mypy"
            ], check=True)
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to set up Poetry: {str(e)}")
            raise

    def _create_file(self, path: Path, content: str):
        """Create a file with given content."""
        self.logger.info(f"Creating {path}")
        with open(path, 'w') as f:
            f.write(content)

    def _get_init_template(self) -> str:
        return '''"""Package exports."""

from .core import main
from .config import Config

__version__ = "0.1.0"
__all__ = ['main', 'Config']
'''

    def _get_main_template(self) -> str:
        return '''"""Entry point for running the package as a module."""
from .core import main

if __name__ == "__main__":
    main()
'''

    def _get_core_template(self) -> str:
        return '''"""Core functionality."""
import logging
import sys
from .config import Config

def setup_logging():
    """Set up logging with console output."""
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)

def main():
    """Main entry point."""
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        
        logger.info("Starting script")
        cfg = Config()
        # Your main logic here
        
    except Exception as e:
        logger.error(f"Script failed: {str(e)}")
        raise
'''

    def _get_config_template(self) -> str:
        return '''"""Configuration management."""
import logging
import os
from pathlib import Path

class Config:
    """Manage configuration settings."""

    def __init__(self):
        """Initialize configuration."""
        self.logger = logging.getLogger(__name__)
        
        # Set up base directories
        self.workspace_dir = Path(os.path.expanduser('~')) / "Library/Mobile Documents/iCloud~md~obsidian/Documents/dev"
        self.app_dir = self.workspace_dir / "scripts" / __package__
        self.output_dir = self.app_dir / "output"
        
        # Ensure directories exist
        os.makedirs(self.output_dir, exist_ok=True)
'''

    def _get_log_handler_template(self) -> str:
        return '''"""Logging configuration."""
import logging
import json
from datetime import datetime

class StructuredLogHandler(logging.Handler):
    """A handler that formats logs in a structured way."""
    
    def __init__(self):
        """Initialize the handler."""
        super().__init__()
        
    def format_record(self, record):
        """Format the log record into a structured format."""
        message = self.format(record) if self.formatter else record.getMessage()
        extra = record.__dict__.get('extra', {})
        
        return {
            "message": message,
            "metadata": {
                "level": record.levelname,
                "logger": record.name,
                "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
                "function": record.funcName,
                **extra
            }
        }
        
    def emit(self, record):
        """Emit a log record."""
        try:
            log_entry = self.format_record(record)
            print(json.dumps(log_entry))
        except Exception as e:
            print(f"Error in log handler: {str(e)}", file=sys.stderr)
'''

    def _get_run_template(self) -> str:
        return f'''#!/usr/bin/env python3
"""
Simple entry point for {self.script_name}.
"""
from {self.script_name}.core import main

if __name__ == "__main__":
    main()
'''

    def _get_test_template(self) -> str:
        return f'''"""Test suite for {self.script_name}."""
import pytest
from {self.script_name}.config import Config

def test_config():
    """Test configuration initialization."""
    cfg = Config()
    assert cfg.app_dir is not None
    assert cfg.output_dir is not None
'''

    def _get_readme_template(self) -> str:
        return f'''# {self.script_name}

## Description
Add your script description here.

## Installation
```bash
poetry install
```

## Usage
```bash
poetry run python run.py
```

Or as a module:
```bash
poetry run python -m {self.script_name}
```

## Development
1. Install dependencies:
   ```bash
   poetry install
   ```

2. Run tests:
   ```bash
   poetry run pytest
   ```

3. Format code:
   ```bash
   poetry run black .
   ```

4. Check types:
   ```bash
   poetry run mypy .
   ```
'''

    def _get_pyproject_template(self) -> str:
        return f'''[tool.poetry]
name = "{self.script_name}"
version = "0.1.0"
description = "Add your description here"
authors = ["Your Name <your.email@example.com>"]

[tool.poetry.dependencies]
python = "^3.8"
python-dotenv = "*"
pyyaml = "*"
psutil = "*"
tqdm = "*"

[tool.poetry.group.dev.dependencies]
pytest = "*"
pytest-cov = "*"
black = "*"
flake8 = "*"
mypy = "*"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
'''

def main():
    """Convert a script to our standardized pattern."""
    if len(sys.argv) != 3:
        print("Usage: python config_and_convert.py <script_name> <script_path>")
        sys.exit(1)
    
    script_name = sys.argv[1]
    script_path = sys.argv[2]
    
    converter = ScriptConverter(script_name, script_path)
    converter.create_directory_structure()
    converter.setup_poetry()
    print(f"\nSuccessfully set up {script_name} with standardized pattern!")

if __name__ == "__main__":
    main() 