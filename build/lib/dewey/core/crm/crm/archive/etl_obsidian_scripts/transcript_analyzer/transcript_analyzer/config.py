"""Configuration management for transcript analyzer."""
import os
from pathlib import Path
import logging
from typing import Optional
import yaml

class Config:
    """Manage configuration settings."""
    
    def __init__(self):
        """Initialize configuration."""
        self.logger = logging.getLogger(__name__)
        
        # Set up base directories
        self.workspace_dir = Path(os.path.expanduser('~')) / "Library/Mobile Documents/iCloud~md~obsidian/Documents/dev"
        self.scripts_dir = self.workspace_dir / "scripts"
        self.app_dir = self.scripts_dir / "transcript_analyzer"
        self.output_dir = self.scripts_dir / "output" / "transcript_analysis"
        self.input_dir = self.app_dir / "input"
        
        # Analysis settings
        self.num_topics = 10
        self.similarity_threshold = 0.3
        self.max_phrase_length = 3
        
        # Load custom config if exists
        self.load_config()
        
        # Ensure directories exist
        self.create_directories()
    
    def load_config(self):
        """Load configuration from YAML file if it exists."""
        config_file = self.app_dir / "config.yml"
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config_data = yaml.safe_load(f)
                
                # Update settings from file
                if config_data:
                    for key, value in config_data.items():
                        if hasattr(self, key):
                            setattr(self, key, value)
                
                self.logger.info("Loaded configuration from file")
            except Exception as e:
                self.logger.error(f"Error loading config file: {str(e)}")
    
    def create_directories(self):
        """Create necessary directories."""
        self.logger.info("Creating required directories")
        
        try:
            # Create main directories
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.input_dir.mkdir(parents=True, exist_ok=True)
            
            # Create subdirectories for different outputs
            (self.output_dir / "topics").mkdir(exist_ok=True)
            (self.output_dir / "summaries").mkdir(exist_ok=True)
            (self.output_dir / "networks").mkdir(exist_ok=True)
            (self.output_dir / "markdown").mkdir(exist_ok=True)
            (self.output_dir / "obsidian_ready").mkdir(exist_ok=True)
            
            self.logger.info("Directory creation complete")
            
        except Exception as e:
            self.logger.error(f"Error creating directories: {str(e)}")
            raise
    
    def validate(self) -> bool:
        """Validate configuration settings."""
        self.logger.info("Validating configuration")
        
        try:
            # Check directory permissions
            if not os.access(self.input_dir, os.R_OK):
                raise ValueError(f"Cannot read from input directory: {self.input_dir}")
            
            if not os.access(self.output_dir, os.W_OK):
                raise ValueError(f"Cannot write to output directory: {self.output_dir}")
            
            # Validate settings
            if not isinstance(self.num_topics, int) or self.num_topics <= 0:
                raise ValueError("num_topics must be a positive integer")
            
            if not isinstance(self.similarity_threshold, float) or not 0 <= self.similarity_threshold <= 1:
                raise ValueError("similarity_threshold must be a float between 0 and 1")
            
            if not isinstance(self.max_phrase_length, int) or self.max_phrase_length <= 0:
                raise ValueError("max_phrase_length must be a positive integer")
            
            self.logger.info("Configuration validation successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {str(e)}")
            raise 