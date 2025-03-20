#!/usr/bin/env python3
"""
Script to reorganize the tests directory structure.

This script will create the new directory structure and move existing
test files to their appropriate locations.
"""

import os
import shutil
from pathlib import Path
import re

# Define the root directory
ROOT_DIR = Path("/Users/srvo/dewey")
TESTS_DIR = ROOT_DIR / "tests"

# Define directory structure
NEW_STRUCTURE = {
    "unit": {
        "core": {
            "db": {},
            "crm": {},
            "bookkeeping": {},
        },
        "llm": {
            "api_clients": {},
        },
        "ui": {
            "components": {},
        },
        "config": {},
        "utils": {},
    },
    "integration": {},
    "functional": {},
}

# Files to move (source, destination)
FILES_TO_MOVE = [
    # Move test_base_script.py to unit/core
    (TESTS_DIR / "test_base_script.py", TESTS_DIR / "unit/core/test_base_script.py"),
    # Move helpers.py to root tests dir (keep in place)
    # (TESTS_DIR / "helpers.py", TESTS_DIR / "helpers.py"),
    # Move test_script_integration.py to integration
    (
        TESTS_DIR / "test_script_integration.py",
        TESTS_DIR / "integration/test_script_integration.py",
    ),
]


def create_directory_structure():
    """Create the new directory structure."""
    print("Creating new directory structure...")

    # Create each directory in the structure
    for top_dir, subdirs in NEW_STRUCTURE.items():
        dir_path = TESTS_DIR / top_dir
        dir_path.mkdir(exist_ok=True)

        # Create __init__.py in each directory
        init_file = dir_path / "__init__.py"
        if not init_file.exists():
            init_file.touch()

        # Create subdirectories
        create_subdirectories(dir_path, subdirs)


def create_subdirectories(parent_dir, subdirs):
    """Recursively create subdirectories."""
    for subdir, nested_subdirs in subdirs.items():
        dir_path = parent_dir / subdir
        dir_path.mkdir(exist_ok=True)

        # Create __init__.py in each directory
        init_file = dir_path / "__init__.py"
        if not init_file.exists():
            init_file.touch()

        # Create nested subdirectories
        if nested_subdirs:
            create_subdirectories(dir_path, nested_subdirs)


def move_files():
    """Move files to their new locations."""
    print("Moving files to new locations...")

    for source, destination in FILES_TO_MOVE:
        if source.exists():
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            shutil.copy2(source, destination)
            print(f"Copied {source} to {destination}")
        else:
            print(f"Warning: Source file {source} does not exist")


def move_directory_contents(source_dir, dest_dir, pattern=None):
    """Move all files from source_dir to dest_dir."""
    if not source_dir.exists():
        print(f"Warning: Source directory {source_dir} does not exist")
        return

    os.makedirs(dest_dir, exist_ok=True)

    for item in source_dir.glob("*"):
        if item.is_file():
            if pattern and not re.search(pattern, item.name):
                continue

            dest_file = dest_dir / item.name
            shutil.copy2(item, dest_file)
            print(f"Copied {item} to {dest_file}")

        elif item.is_dir() and item.name != "__pycache__":
            nested_dest_dir = dest_dir / item.name
            move_directory_contents(item, nested_dest_dir, pattern)


def move_existing_tests():
    """Move existing tests to their new locations."""
    print("Moving existing tests to new locations...")

    # Move tests/core to tests/unit/core
    move_directory_contents(
        TESTS_DIR / "core",
        TESTS_DIR / "unit/core",
        pattern=r"test_.*\.py$|conftest\.py$",
    )

    # Move tests/dewey/core to tests/unit/core
    move_directory_contents(
        TESTS_DIR / "dewey/core",
        TESTS_DIR / "unit/core",
        pattern=r"test_.*\.py$|conftest\.py$",
    )

    # Move tests/dewey/llm to tests/unit/llm
    move_directory_contents(
        TESTS_DIR / "dewey/llm",
        TESTS_DIR / "unit/llm",
        pattern=r"test_.*\.py$|conftest\.py$",
    )

    # Move tests/ui to tests/unit/ui
    if (TESTS_DIR / "ui").exists():
        move_directory_contents(
            TESTS_DIR / "ui",
            TESTS_DIR / "unit/ui",
            pattern=r"test_.*\.py$|conftest\.py$",
        )

    # Move tests/config to tests/unit/config
    if (TESTS_DIR / "config").exists():
        move_directory_contents(
            TESTS_DIR / "config",
            TESTS_DIR / "unit/config",
            pattern=r"test_.*\.py$|conftest\.py$",
        )


def consolidate_conftest():
    """Consolidate conftest.py files."""
    print("Consolidating conftest.py files...")

    # Check if there's a conftest.py in tests/dewey
    dewey_conftest = TESTS_DIR / "dewey/conftest.py"
    main_conftest = TESTS_DIR / "conftest.py"

    if dewey_conftest.exists():
        if not main_conftest.exists():
            shutil.copy2(dewey_conftest, main_conftest)
            print(f"Copied {dewey_conftest} to {main_conftest}")
        else:
            print(f"Warning: Both {dewey_conftest} and {main_conftest} exist.")
            print("Please manually merge them.")


def main():
    """Main function to reorganize tests."""
    print("Starting test directory reorganization...")

    # Create the new directory structure
    create_directory_structure()

    # Move specific files
    move_files()

    # Move existing tests
    move_existing_tests()

    # Consolidate conftest.py files
    consolidate_conftest()

    print("\nReorganization complete!")
    print("\nImportant: This script only copied files to the new locations.")
    print("It did not delete any original files or directories.")
    print("You should manually verify that everything was moved correctly")
    print("before deleting the original files and directories.")


if __name__ == "__main__":
    main()
