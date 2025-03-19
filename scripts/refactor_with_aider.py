#!/usr/bin/env python3

"""
Simplified script refactoring using BaseScript import detection and original repo matching.
"""

import re
import argparse
import logging
import shutil
from pathlib import Path
from typing import Optional, Set, List, Dict, Any
import difflib

from aider.coders import Coder
from aider.models import Model
from aider.io import InputOutput
from dewey.core.base_script import BaseScript


# Paths
CURRENT_REPO = Path.cwd()
ORIGINAL_REPO = Path("/Users/srvo/dewey/dewey_original")
TEMP_DIR = CURRENT_REPO / "refactor_temp"

class ScriptRefactorer(BaseScript):
    config_section = "script_refactorer"

    def __init__(self, dry_run: bool = False, **kwargs: Any):
        """
        Initializes the ScriptRefactorer.

        Args:
            dry_run (bool): If True, simulates changes without modifying files.
            **kwargs (Any): Additional keyword arguments for BaseScript.
        """
        super().__init__(**kwargs)
        self.dry_run = dry_run
        self.processed_files: Set[Path] = set()
        
    def find_basescript_imports(self) -> Set[Path]:
        """
        Finds files with only BaseScript import and no proper implementation.

        Returns:
            Set[Path]: A set of file paths that import BaseScript but don't implement it correctly.
        """
        target_files = set()
        current_script = Path(__file__).resolve()
        
        for py_file in CURRENT_REPO.rglob("*.py"):
            # Skip self
            if py_file == current_script:
                continue
            
            try:
                # Handle file encoding
                with open(py_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    
                if "from dewey.core.base_script import BaseScript" in content:
                    if not re.search(r"class \w+\(BaseScript\):", content):
                        target_files.add(py_file)
                        self.logger.info(f"Found incomplete BaseScript file: {py_file}")
                        
            except UnicodeDecodeError:
                self.logger.warning(f"Skipping {py_file} - invalid UTF-8 encoding")
            except Exception as e:
                self.logger.error(f"Error reading {py_file}: {e}")
            
        return target_files

    def find_original_file(self, current_file: Path) -> Optional[Path]:
        """
        Finds the matching file in the original repository.

        Args:
            current_file (Path): The path to the file in the current repository.

        Returns:
            Optional[Path]: The path to the matching file in the original repository, or None if not found.
        """
        rel_path = current_file.relative_to(CURRENT_REPO)
        original_path = ORIGINAL_REPO / rel_path
        
        if original_path.exists():
            return original_path
            
        # Try fuzzy matching for file names
        filename = current_file.name
        possible_matches = list(ORIGINAL_REPO.rglob(filename))
        
        if len(possible_matches) == 1:
            return possible_matches[0]
            
        if len(possible_matches) > 1:
            self.logger.warning(f"Multiple matches for {filename} in original repo")
            return None
            
        return None

    def refactor_with_aider(self, original_file: Path) -> bool:
        """
        Refactors a file using Aider's Python API.

        Args:
            original_file (Path): The path to the original file to refactor.

        Returns:
            bool: True if refactoring was successful, False otherwise.
        """
        try:
            # Skip binary files
            if original_file.suffix != ".py":
                return False
            
            # Create temp copy with proper encoding
            temp_file = TEMP_DIR / original_file.name
            with open(original_file, "r", encoding="utf-8", errors="ignore") as src:
                with open(temp_file, "w", encoding="utf-8") as dst:
                    dst.write(src.read())
                
            # Setup Aider with minimal configuration
            io = InputOutput(yes=True)  # Auto-confirm changes
            model = Model()  # Use default configured model
            
            # Create coder with only essential parameters
            coder = Coder.create(
                model=model,
                fnames=[str(temp_file)],
                io=io
            )

            # Single focused instruction per Aider's recommendations
            instructions = (
                "Refactor this script to properly implement Dewey conventions by:\n"
                "1. Inheriting from BaseScript with config_section\n"
                "2. Implementing required run() method\n"
                "3. Using self.logger instead of print/logging\n"
                "4. Accessing config via self.get_config_value()\n"
                "5. Adding Google-style docstrings with Args/Returns/Raises"
            )

            if self.dry_run:
                self.logger.info(f"[DRY RUN] Would refactor {original_file.name}")
                return True

            # Execute single focused instruction
            coder.run(instructions)
            
            if coder.dirty:
                with open(temp_file, "w") as f:
                    f.write(coder.get_file_contents(str(temp_file)))
                return True
                
            return False

        except Exception as e:
            self.logger.error(f"Error refactoring {original_file}: {e}")
            return False

    def replace_current_file(self, current_file: Path, original_file: Path) -> None:
        """
        Replaces the current file with the refactored original.

        Args:
            current_file (Path): The path to the file in the current repository.
            original_file (Path): The path to the original file in the original repository.
        """
        try:
            refactored_file = TEMP_DIR / original_file.name
            
            if self.dry_run:
                self.logger.info(f"[DRY RUN] Would replace {current_file} with refactored version")
                return

            shutil.copy2(refactored_file, current_file)
            self.logger.info(f"Successfully updated {current_file}")

        except Exception as e:
            self.logger.error(f"Error replacing file: {e}")

    def run(self) -> None:
        """
        Main refactoring workflow.
        """
        self.logger.info("Starting simplified refactoring process")
        
        # Find all current files with incomplete BaseScript usage
        current_files = self.find_basescript_imports()
        self.logger.info(f"Found {len(current_files)} files needing refactoring")

        for current_file in current_files:
            # Find matching original file
            original_file = self.find_original_file(current_file)
            if not original_file:
                self.logger.warning(f"No original found for {current_file}")
                continue

            # Refactor original file
            success = self.refactor_with_aider(original_file)
            if not success:
                continue

            # Replace current file with refactored original
            self.replace_current_file(current_file, original_file)
            self.processed_files.add(current_file)

        self.logger.info(f"Processed {len(self.processed_files)} files")
        if self.dry_run:
            self.logger.info("DRY RUN COMPLETE - No changes made")

def main():
    parser = argparse.ArgumentParser(description="Refactor scripts using original versions")
    parser.add_argument("--dry-run", action="store_true", help="Simulate changes")
    args = parser.parse_args()

    refactorer = ScriptRefactorer(dry_run=args.dry_run)
    refactorer.run()

if __name__ == "__main__":
    main()
