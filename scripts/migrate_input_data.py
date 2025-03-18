#!/usr/bin/env python3

"""
Script to migrate data from input_data directory to MotherDuck.
Uses the BaseScript's MotherDuckEngine for safe data migration.
"""

import os
from pathlib import Path
from dewey.core.base_script import BaseScript

INPUT_DATA_DIR = "/Users/srvo/input_data"

class DataMigrationScript(BaseScript):
    """Script to migrate data from input directory to MotherDuck."""
    
    def __init__(self):
        """Initialize the data migration script."""
        super().__init__(
            name="data_migrator",
            description="Migrate data from input directory to MotherDuck"
        )
    
    def run(self) -> None:
        """Run the data migration."""
        input_dir = Path(INPUT_DATA_DIR)
        if not input_dir.exists():
            raise FileNotFoundError(f"Input directory not found: {INPUT_DATA_DIR}")
        
        self.logger.info("Starting data migration to MotherDuck")
        
        # Use the database engine from BaseScript
        engine = self.db_engine
        
        # Upload all files in the input directory
        total_files = 0
        success_files = 0
        
        # Process all files in the directory
        for file_path in input_dir.rglob('*'):
            if file_path.is_file() and not file_path.name.startswith('.'):
                total_files += 1
                try:
                    if engine.upload_file(str(file_path)):
                        success_files += 1
                        # Delete source file after successful upload
                        file_path.unlink()
                        self.logger.info(f"Successfully processed and deleted: {file_path}")
                    else:
                        self.logger.error(f"Failed to upload: {file_path}")
                except Exception as e:
                    self.logger.error(f"Error processing {file_path}: {str(e)}")
        
        # Log results
        if total_files == success_files:
            self.logger.info(f"Successfully migrated all {total_files} files")
        else:
            self.logger.warning(f"Migrated {success_files} out of {total_files} files")
            if success_files < total_files:
                raise RuntimeError("Some files failed to migrate")

if __name__ == "__main__":
    DataMigrationScript().main() 