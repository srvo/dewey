#!/usr/bin/env python
"""Legacy code refactoring script following Dewey project conventions."""
from __future__ import annotations
from datetime import datetime
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
REFACTOR_PREFIX = "RF_"


class LegacyRefactor:
    """Handles refactoring of legacy hash-suffixed files."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.legacy_files = self.find_legacy_files()
        self.decision_log = []
        self.log_file = Path("refactor_decisions.log")
        # Initialize log with header
        if not self.log_file.exists():
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.write("timestamp,source_path,original_target,final_target,conflict_detected,action_taken\n")
        
    def find_legacy_files(self) -> List[Path]:
        """Find all files in consolidated_functions directory."""
        files = list(CODE_CONSOLIDATION_DIR.glob("*.py"))
        logger.info(f"Found {len(files)} files in consolidated_functions directory")
        for f in files:
            logger.debug(f"Processing file: {f}")
        return files

    def validate_target(self, target: Path) -> None:
        """Ensure target path follows project conventions."""
        if not target.parent.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory {target.parent}")

    def relocate_file(self, source: Path) -> Optional[Path]:
        """Move legacy file to appropriate directory with proper naming."""
        try:
            base_name = HASH_PATTERN.sub("", source.name)
            
            # Read file content for additional heuristics
            with open(source, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Determine target directory based on multiple heuristics
            if self._is_test_file(base_name, content):
                target_dir = Path("tests/legacy")
            elif self._is_llm_related(base_name, content):
                target_dir = Path("src/dewey/llm/legacy")
            elif self._is_core_module(base_name, content):
                target_dir = Path("src/dewey/core/legacy")
            elif self._has_existing_implementation(base_name):
                target_dir = Path("src/dewey/refactor")
                base_name = f"{REFACTOR_PREFIX}{base_name}"
            else:
                target_dir = Path("src/dewey/legacy_functions")
            
            # Ensure unique filename
            target, original_target, conflict = self._get_unique_filename(target_dir, base_name)
            self.validate_target(target)
            
            # Log decision making
            self._log_decision(
                source=source,
                original_target=original_target,
                final_target=target,
                conflict_detected=conflict,
                action_taken="moved" if not conflict else "renamed"
            )
            
            if not self.dry_run:
                shutil.move(str(source), str(target))
                logger.info(f"Successfully moved {source} -> {target}")
                
                # Add refactoring metadata
                self._add_refactoring_metadata(target, source.name)
            return target
        except Exception as e:
            logger.error(f"Failed to relocate {source}: {str(e)}")
            return None

    def _is_test_file(self, filename: str, content: str) -> bool:
        """Check if file is test-related using name and content."""
        test_indicators = {"test", "spec", "fixture", "mock", "stub"}
        name_match = any(indicator in filename.lower() for indicator in test_indicators)
        content_match = any(
            keyword in content.lower() 
            for keyword in ["pytest", "unittest", "assert", "mock", "patch"]
        )
        return name_match or content_match

    def _is_llm_related(self, filename: str, content: str) -> bool:
        """Check if file is LLM-related using name and content."""
        llm_indicators = {"llm", "prompt", "model", "generation", "completion"}
        name_match = any(indicator in filename.lower() for indicator in llm_indicators)
        content_match = any(
            keyword in content.lower()
            for keyword in ["deepinfra", "openai", "gemini", "llm", "language model"]
        )
        return name_match or content_match

    def _is_core_module(self, filename: str, content: str) -> bool:
        """Check if file belongs to core modules."""
        core_indicators = {"crm", "accounting", "research", "automation"}
        name_match = any(indicator in filename.lower() for indicator in core_indicators)
        content_match = any(
            keyword in content.lower()
            for keyword in ["core.", "crm.", "accounting.", "research.", "automation."]
        )
        return name_match or content_match

    def _has_existing_implementation(self, filename: str) -> bool:
        """Check if a non-refactored version already exists."""
        search_dirs = [
            Path("src/dewey/llm/agents"),
            Path("src/dewey/core"),
            Path("src/dewey/pipeline"),
            Path("src/dewey/utils")
        ]
        return any((d / f"{filename}.py").exists() for d in search_dirs)

    def _get_unique_filename(self, target_dir: Path, base_name: str) -> Path:
        """Generate unique filename with conflict resolution."""
        original_target = target_dir / f"{base_name}.py"
        target = original_target
        conflict = False
        
        if target.exists():
            base_name += "_tocheck"
            target = target_dir / f"{base_name}.py"
            conflict = True
            # If _tocheck version exists, add counter
            counter = 1
            while target.exists():
                target = target_dir / f"{base_name}_{counter}.py"
                counter += 1
                
        return target, original_target, conflict

    def _add_refactoring_metadata(self, target: Path, original_name: str) -> None:
        """Add refactoring metadata as a comment at the top of the file."""
        metadata = f"""
# Refactored from: {original_name}
# Date: {datetime.now().isoformat()}
# Refactor Version: 1.0
"""
        with open(target, 'r+', encoding='utf-8') as f:
            content = f.read()
            f.seek(0, 0)
            f.write(metadata + content)

    def _log_decision(self, source: Path, original_target: Path, final_target: Path, 
                    conflict_detected: bool, action_taken: str) -> None:
        """Log refactoring decisions for future analysis."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "source_path": str(source),
            "original_target": str(original_target),
            "final_target": str(final_target),
            "conflict_detected": str(conflict_detected),
            "action_taken": action_taken
        }
        self.decision_log.append(log_entry)
        
        # Append to log file
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(",".join(log_entry.values()) + "\n")

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
        logger.info(f"Starting processing of {len(self.legacy_files)} legacy files")
        if not self.legacy_files:
            logger.warning("No legacy files found to process")
            return
            
        for legacy_file in self.legacy_files:
            logger.info(f"Processing {legacy_file}")
            if target := self.relocate_file(legacy_file):
                self.update_references(legacy_file, target)
        logger.info(f"Completed processing {len(self.legacy_files)} files")

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
