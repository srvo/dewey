import os
from pathlib import Path
import logging
from datetime import datetime
import spacy

class FileAnalyzer:
    """Analyze files in a directory."""
    
    def __init__(self, dry_run: bool = False, output_dir: str = None):
        """Initialize the analyzer."""
        self.dry_run = dry_run
        
        # Set up base directories
        self.workspace_dir = Path(os.path.expanduser('~')) / "Library/Mobile Documents/iCloud~md~obsidian/Documents/dev"
        self.scripts_dir = self.workspace_dir / "scripts"
        
        # Use standardized output directory with descriptive subfolder
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = self.scripts_dir / "output" / "file_analysis"
            
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.logger = logging.getLogger(__name__)
        self.nlp = spacy.load('en_core_web_sm')
        self.reflection_config = ReflectionConfig()
        
        # Progress tracking
        self.progress_file = self.output_dir / 'progress.json'
        self.last_save_time = datetime.now()
        self.save_interval = 60  # Save progress every 60 seconds 