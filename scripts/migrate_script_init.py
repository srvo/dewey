#!/usr/bin/env python3

"""
Script to migrate existing script initialization to the new BaseScript interface.

This updates scripts using the old BaseScript initialization pattern to the new
pattern that supports:
- config_section parameter
- requires_db parameter
- enable_llm parameter

Usage:
  python scripts/migrate_script_init.py [--dry-run]
"""

import argparse
import re
from pathlib import Path
from typing import List

# Import the BaseScript class from our custom implementation to avoid circular imports
import abc
import logging

class BaseScript(abc.ABC):
    """Minimal implementation for the script."""
    
    def __init__(self, name=None, description=None):
        """Function __init__."""
        self.name = name
        self.description = description
        self.logger = logging.getLogger(name or self.__class__.__name__)
        
    @abc.abstractmethod
    def run(self):
        """Function run."""
        pass


class ScriptInitMigrator(BaseScript):
    """Migrates scripts to the new BaseScript initialization pattern."""
    
    def __init__(self, dry_run=False):
        """Function __init__."""
        super().__init__(
            name="script_migrator",
            description="Migrates scripts to the new BaseScript initialization pattern"
        )
        self.dry_run = dry_run
        self.updated_files = []
        self.skipped_files = []
        self.error_files = []
        
    def find_script_files(self) -> List[Path]:
        """Find script files that might need migration."""
        script_files=None, root_dir / "src" / "dewey" / "maintenance", root_dir / "src" / "dewey" / "llm", root_dir / "scripts"
        ]
        
        for script_dir in script_dirs:
            if not script_dir.exists():
                if self) -> List[Path]:
        """Find script files that might need migration."""
        script_files is None:
                    self) -> List[Path]:
        """Find script files that might need migration."""
        script_files = []
        root_dir = Path(__file__).parent.parent
        
        script_dirs = [
            root_dir / "src" / "dewey" / "core"
                continue
                
            for file in script_dir.glob("**/*.py"):
                # Skip __init__.py and special files
                if file.name.startswith("__") or file.name == "base_script.py":
                    continue
                    
                script_files.append(file)
                
        return script_files
        
    def needs_migration(self, file_content: str) -> bool:
        """Check if a file needs migration."""
        # Check for BaseScript import
        if "from dewey.core.base_script import BaseScript" not in file_content:
            return False
            
        # Check for inheritance from BaseScript using regex
        class_pattern = r"class\s+(\w+)\s*\(.*BaseScript.*\):"
        if not re.search(class_pattern, file_content):
            return False
            
        # Look for super().__init__ pattern without new parameters
        init_pattern = r"super\(\).__init__\s*\(\s*(?:name\s*=\s*[\'\"].*?[\'\"])?(?:\s*,\s*description\s*=\s*[\'\"].*?[\'\"])?\s*\)"
        return bool(re.search(init_pattern, file_content))
        
    def migrate_file(self, file_path: Path) -> bool:
        """Migrate a single file to use the new BaseScript interface."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                
            if not self.needs_migration(content):
                self.logger.info(f"Skipping {file_path} - no migration needed")
                self.skipped_files.append(file_path)
                return False
                
            # Use regex to handle the migration
            updated_content = content
            
            # Find class inheritance and determine if it uses config, db, llm
            class_pattern = r"class\s+(\w+)\s*\(.*BaseScript.*\):"
            class_match = re.search(class_pattern, content)
            if not class_match:
                # Shouldn't happen since we checked in needs_migration
                return False
                
            class_name = class_match.group(1)
            
            # Detect if class uses config, db, llm
            uses_config = "self.config" in content
            uses_db = "self.db_conn" in content
            uses_llm = "self.llm_client" in content
            
            # Find the current super().__init__ call
            init_pattern = r"(super\(\).__init__\s*\()(\s*(?:name\s*=\s*[\'\"].*?[\'\"])?(?:\s*,\s*description\s*=\s*[\'\"].*?[\'\"])?)(\s*\))"
            init_match = re.search(init_pattern, content)
            
            if not init_match:
                self.logger.warning(f"Could not find super().__init__ call in {file_path}")
                self.skipped_files.append(file_path)
                return False
                
            # Build the new init arguments
            pre, args, post = init_match.groups()
            new_args = args.strip()
            
            if uses_config and "config_section" not in new_args:
                config_section = self._guess_config_section(class_name)
                if new_args:
                    new_args += ",\n            "
                new_args += f"config_section='{config_section}'"
                
            if uses_db and "requires_db" not in new_args:
                if new_args:
                    new_args += ",\n            "
                new_args += "requires_db=True"
                
            if uses_llm and "enable_llm" not in new_args:
                if new_args:
                    new_args += ",\n            "
                new_args += "enable_llm=True"
                
            # Replace the init call
            updated_content = re.sub(
                init_pattern,
                f"{pre}{new_args}{post}",
                content
            )
            
            if content == updated_content:
                self.logger.info(f"No changes needed for {file_path}")
                self.skipped_files.append(file_path)
                return False
                
            # Write changes
            if not self.dry_run:
                with open(file_path, 'w') as f:
                    f.write(updated_content)
                    
            self.logger.info(f"Updated {file_path}")
            self.updated_files.append(file_path)
            return True
            
        except Exception as e:
            self.logger.error(f"Error migrating {file_path}: {str(e)}")
            self.error_files.append(file_path)
            return False
            
    def _guess_config_section(self, class_name: str) -> str:
        """Guess a reasonable config section name based on class name."""
        # Convert CamelCase to snake_case
        name = re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).lower()
        
        # Remove common suffixes
        for suffix in ['script', 'updater', 'migrator', 'processor', 'handler', 'manager']:
            if name.endswith(f"_{suffix}"):
                name = name[:-len(suffix)-1]
                break
                
        return name
            
    def run(self) -> None:
        """Run the migration script."""
        self.logger.info("Starting script migration")
        
        script_files = self.find_script_files()
        self.logger.info(f"Found {len(script_files)} potential script files")
        
        for file_path in script_files:
            self.migrate_file(file_path)
            
        # Print summary
        self.logger.info("\nMigration complete!")
        self.logger.info(f"Updated {len(self.updated_files)} files")
        self.logger.info(f"Skipped {len(self.skipped_files)} files")
        self.logger.info(f"Errors in {len(self.error_files)} files")
        
        if self.error_files:
            self.logger.warning("\nFiles with errors:")
            for file in self.error_files:
                self.logger.warning(f"  {file}")
                
        if self.dry_run:
            self.logger.info("\nThis was a dry run. No files were modified.")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate scripts to new BaseScript initialization pattern"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print changes without modifying files"
    )
    args = parser.parse_args()
    
    migrator = ScriptInitMigrator(dry_run=args.dry_run)
    migrator.run()


if __name__ == "__main__":
    main() 