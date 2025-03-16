#!/usr/bin/env python
"""Legacy code refactoring script following Dewey project conventions."""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

import logging
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

CODE_CONSOLIDATION_DIR = Path("src/dewey/consolidated_functions")
HASH_PATTERN = re.compile(r"_([0-9a-fA-F]{8})\.py$")


class LegacyRefactor:
    """Handles refactoring of legacy hash-suffixed files."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.legacy_files = self.find_legacy_files()
        
    def find_legacy_files(self) -> List[Path]:
        """Find all legacy files using hash suffix pattern."""
        return [
            p for p in Path("src").rglob("*.py")
            if HASH_PATTERN.search(p.name)
        ]

    def validate_target(self, target: Path) -> None:
        """Ensure target path follows project conventions."""
        if not target.parent.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory {target.parent}")

    def relocate_file(self, source: Path) -> Optional[Path]:
        """Move legacy file to consolidated_functions with proper naming."""
        try:
            new_name = HASH_PATTERN.sub("", source.name)
            target = CODE_CONSOLIDATION_DIR / new_name
            
            self.validate_target(target)
            
            if not self.dry_run:
                shutil.move(str(source), str(target))
                logger.info(f"Moved {source} -> {target}")
            return target
        except Exception as e:
            logger.error(f"Failed to relocate {source}: {str(e)}")
            return None

    def update_references(self, old_path: Path, new_path: Path) -> None:
        """Update imports and references using Ruff."""
        if not self.dry_run:
            try:
                subprocess.run([
                    "ruff", "check", "--select", "TCH", 
                    "--fix", "--unsafe-fixes", str(old_path.parent)
                ], check=True)
                logger.info(f"Updated references for {new_path}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Reference update failed: {str(e)}")

    def process_files(self) -> None:
        """Main processing pipeline."""
        for legacy_file in self.legacy_files:
            if target := self.relocate_file(legacy_file):
                self.update_references(legacy_file, target)

def main():
    """CLI entry point with dry-run support."""
    parser = argparse.ArgumentParser(description="Legacy code refactoring tool")
    parser.add_argument("--dry-run", action="store_true", help="Simulate changes")
    args = parser.parse_args()

    refactor = LegacyRefactor(args.dry_run)
    refactor.process_files()

    if args.dry_run:
        print("[Dry Run] Would process files:")
        for f in refactor.legacy_files:
            print(f" - {f}")

if __name__ == "__main__":
    main()
