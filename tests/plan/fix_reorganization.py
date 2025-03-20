#!/usr/bin/env python3
"""
Script to fix the test directory reorganization.
This script properly moves tests from the backup directory to the new structure,
fixing import paths and ensuring tests can run in the new structure.
"""

import os
import shutil
from pathlib import Path
import re
import sys

# Base paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
BACKUP_DIR = Path("/Users/srvo/dewey/tests/backup_20250319_181609")
NEW_TEST_BASE = "tests"

# Map from backup directories to new directories
DIR_MAPPING = {
    # Core directories
    f"{BACKUP_DIR}/core": "tests/unit/core",
    f"{BACKUP_DIR}/dewey/core": "tests/unit/core",
    
    # Config directories
    f"{BACKUP_DIR}/config": "tests/unit/config",
    f"{BACKUP_DIR}/dewey/dewey/config": "tests/unit/config",
    
    # LLM directories
    f"{BACKUP_DIR}/dewey/dewey/llm": "tests/unit/llm",
    f"{BACKUP_DIR}/dewey/llm": "tests/unit/llm",
    
    # UI directories
    f"{BACKUP_DIR}/ui": "tests/unit/ui",
    f"{BACKUP_DIR}/dewey/dewey/ui": "tests/unit/ui",
    
    # Other directories
    f"{BACKUP_DIR}/dewey/dewey/utils": "tests/unit/utils",
    f"{BACKUP_DIR}/docs": "tests/unit/docs",
}

# Files that should be at the root of the tests directory
ROOT_FILES = [
    f"{BACKUP_DIR}/conftest.py",
    f"{BACKUP_DIR}/helpers.py",
]


def fix_imports(file_path, old_path, new_path):
    """Fix import statements in the test file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Replace imports if needed
        modified = False
        
        # Fix from dewey.core imports
        if "from dewey." in content or "import dewey." in content:
            # No change needed for src imports since they're using the correct structure
            pass
        
        # Fix relative imports if needed
        if "from .." in content or "from ." in content:
            # This is more complex and would need detailed analysis
            # For now, we'll log these files for manual review
            print(f"WARNING: File {file_path} contains relative imports that may need manual inspection")
        
        # Update any paths referencing the old test structure
        old_rel_path = str(old_path).replace(str(BACKUP_DIR), 'tests')
        new_rel_path = str(new_path)
        if old_rel_path.replace('tests/', '') in content:
            content = content.replace(old_rel_path.replace('tests/', ''), new_rel_path.replace('tests/', ''))
            modified = True

        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated imports in {file_path}")
    except UnicodeDecodeError:
        print(f"WARNING: Could not read {file_path} as text, skipping import fixes")


def ensure_init_files(directory):
    """Ensure that all directories have __init__.py files."""
    for root, dirs, _ in os.walk(directory):
        for d in dirs:
            init_file = os.path.join(root, d, "__init__.py")
            if not os.path.exists(init_file):
                with open(init_file, 'w', encoding='utf-8') as f:
                    f.write("# Automatically generated __init__.py file\n")
                print(f"Created __init__.py in {os.path.join(root, d)}")


def copy_test_file(source, target, old_path, new_path):
    """Copy a test file and fix imports."""
    os.makedirs(os.path.dirname(target), exist_ok=True)
    
    # Only copy if target doesn't exist or source is newer
    if not os.path.exists(target) or os.path.getmtime(source) > os.path.getmtime(target):
        shutil.copy2(source, target)
        print(f"Copied {source} -> {target}")
        
        # Fix imports in the copied file
        fix_imports(target, old_path, new_path)
    else:
        print(f"Skipped existing file: {target}")


def is_test_file(filename):
    """Check if a file is a test file."""
    return (
        filename.startswith("test_") and filename.endswith(".py") or
        filename == "conftest.py"
    )


def process_directory(old_path, new_path):
    """Process a directory, copying test files and recursing into subdirectories."""
    old_path = Path(old_path)
    new_path = Path(new_path)
    
    if not old_path.exists():
        print(f"WARNING: Old path {old_path} does not exist, skipping")
        return
    
    print(f"Processing directory: {old_path} -> {new_path}")
    
    # Ensure the target directory exists
    os.makedirs(new_path, exist_ok=True)
    
    # Process all files in the directory
    for item in old_path.iterdir():
        if item.is_file() and is_test_file(item.name):
            target = new_path / item.name
            copy_test_file(item, target, old_path, new_path)
        elif item.is_dir() and item.name != "__pycache__" and not item.name.startswith("."):
            # Determine the target directory path
            target_dir = new_path / item.name
            
            # Check if there's a specific mapping for this subdirectory
            full_old_subdir = str(old_path / item.name)
            if full_old_subdir in DIR_MAPPING:
                target_dir = Path(DIR_MAPPING[full_old_subdir])
            
            # Recurse into the subdirectory
            process_directory(item, target_dir)


def copy_root_files():
    """Copy files that should be at the root of the tests directory."""
    for root_file in ROOT_FILES:
        source = Path(root_file)
        if source.exists():
            target = PROJECT_ROOT / "tests" / source.name
            if not target.exists() or os.path.getmtime(source) > os.path.getmtime(target):
                shutil.copy2(source, target)
                print(f"Copied root file: {source} -> {target}")
            else:
                print(f"Skipped existing root file: {target}")
        else:
            print(f"WARNING: Root file {source} does not exist, skipping")


def main():
    """Main entry point for the script."""
    # Make sure we're in the project root directory
    os.chdir(PROJECT_ROOT)
    
    # Verify backup directory exists
    if not BACKUP_DIR.exists():
        print(f"ERROR: Backup directory {BACKUP_DIR} does not exist!")
        print("Please provide the correct path to the backup directory.")
        sys.exit(1)
    
    # Create the new test directories if they don't exist
    for test_type in ["unit", "integration", "functional"]:
        os.makedirs(f"{NEW_TEST_BASE}/{test_type}", exist_ok=True)
    
    # Copy root test files (like conftest.py)
    copy_root_files()
    
    # Process each directory in the backup
    for backup_subdir in BACKUP_DIR.iterdir():
        if backup_subdir.is_dir() and not backup_subdir.name.startswith('.'):
            # Check if there's a mapping for this directory
            backup_path = str(backup_subdir)
            if backup_path in DIR_MAPPING:
                new_dir = DIR_MAPPING[backup_path]
                process_directory(backup_path, new_dir)
            else:
                print(f"WARNING: No mapping defined for {backup_path}")
    
    # Ensure all directories have __init__.py files
    ensure_init_files(NEW_TEST_BASE)
    
    print("\nReorganization fix complete!")
    print("You may need to manually verify some files with complex imports.")
    print("Remember to run 'pytest tests/unit' to validate the reorganization.")


if __name__ == "__main__":
    main() 