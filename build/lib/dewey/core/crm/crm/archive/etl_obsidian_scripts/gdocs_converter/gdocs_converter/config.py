"""
Configuration management for the Google Docs converter.
"""
import logging
import os
from pathlib import Path
from typing import Dict
import yaml

class Config:
    """Manage configuration settings for the application."""

    def __init__(self):
        """Initialize configuration with default values."""
        self.logger = logging.getLogger(__name__)
        
        # Set up base directories
        self.workspace_dir = Path(os.path.expanduser('~')) / "Library/Mobile Documents/iCloud~md~obsidian/Documents/dev"
        self.scripts_dir = self.workspace_dir / "scripts"
        self.app_dir = self.scripts_dir / "gdocs_converter"
        self.output_dir = self.scripts_dir / "output" / "gdocs_converted"
        self.credentials_path = self.workspace_dir / "credentials/google_credentials.json"
        
        # Ensure directories exist
        self._create_directories()
        
        self.logger.info("Configuration initialized", extra={
            "component": "config",
            "action": "initialize",
            "paths": {
                "workspace_dir": str(self.workspace_dir),
                "app_dir": str(self.app_dir),
                "output_dir": str(self.output_dir),
                "credentials_path": str(self.credentials_path)
            }
        })

    def _create_directories(self):
        """Create necessary directories if they don't exist."""
        try:
            self.logger.info("Creating required directories", extra={
                "component": "config",
                "action": "create_directories"
            })
            
            directories = [
                self.app_dir,
                self.output_dir,
                self.output_dir / "raw_markdown",
                self.output_dir / "obsidian_ready"
            ]
            
            for directory in directories:
                if not os.path.exists(directory):
                    self.logger.info(f"Creating directory: {directory}", extra={
                        "component": "config",
                        "action": "create_directory",
                        "path": str(directory)
                    })
                    os.makedirs(directory)
                    
            self.logger.info("Directory creation complete", extra={
                "component": "config",
                "action": "create_directories",
                "status": "success"
            })
            
        except Exception as e:
            self.logger.error("Failed to create directories", extra={
                "component": "config",
                "action": "create_directories",
                "status": "error",
                "error_type": type(e).__name__,
                "error_details": str(e)
            })
            raise

    def validate(self):
        """Validate the configuration."""
        try:
            self.logger.info("Validating configuration", extra={
                "component": "config",
                "action": "validate"
            })
            
            # Check if credentials file exists
            if not os.path.exists(self.credentials_path):
                msg = f"Credentials file not found at: {self.credentials_path}"
                self.logger.error(msg, extra={
                    "component": "config",
                    "action": "validate",
                    "status": "error",
                    "error_type": "FileNotFoundError",
                    "credentials_path": str(self.credentials_path)
                })
                raise FileNotFoundError(msg)
            
            # Check if directories are writable
            for directory in [self.app_dir, self.output_dir]:
                if not os.access(directory, os.W_OK):
                    msg = f"Directory not writable: {directory}"
                    self.logger.error(msg, extra={
                        "component": "config",
                        "action": "validate",
                        "status": "error",
                        "error_type": "PermissionError",
                        "directory": str(directory)
                    })
                    raise PermissionError(msg)
            
            self.logger.info("Configuration validation successful", extra={
                "component": "config",
                "action": "validate",
                "status": "success"
            })
            
        except Exception as e:
            self.logger.error("Configuration validation failed", extra={
                "component": "config",
                "action": "validate",
                "status": "error",
                "error_type": type(e).__name__,
                "error_details": str(e)
            })
            raise

    def __str__(self):
        """Return a string representation of the configuration."""
        return f"Config(workspace_dir={self.workspace_dir}, app_dir={self.app_dir}, output_dir={self.output_dir}, credentials_path={self.credentials_path})" 