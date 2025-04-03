#!/usr/bin/env python
"""Fix docstring formatting issues using Ruff's built-in capabilities.

This script automatically fixes docstring issues by:
1. Running Ruff's linter with docstring rules to fix common formatting issues
2. Running Ruff's formatter to ensure consistent code and docstring format

This is much more robust than custom AST manipulation and prevents
syntax errors from being introduced into the code.

Run with: python scripts/fix_docstrings.py [file_or_directory_paths...]
If no path is provided, it will process the current directory.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


def fix_docstrings(file_path: Path) -> Tuple[bool, str]:
    """Fix docstring issues in a file using Ruff.

    Args:
        file_path: Path to the Python file to process

    Returns:
        A tuple of (success, message)

    """
    try:
        # First run Ruff's linter with docstring rules and fix option
        linter_result = subprocess.run(
            ["ruff", "check", str(file_path), "--select=D", "--fix"],
            capture_output=True,
            text=True,
            check=False,
        )

        # Then run Ruff's formatter to ensure consistent formatting
        formatter_result = subprocess.run(
            ["ruff", "format", str(file_path)],
            capture_output=True,
            text=True,
            check=False,
        )

        # Check if either operation modified the file
        fixed = (
            linter_result.returncode == 0 and "1 fixed" in linter_result.stderr
        ) or (formatter_result.returncode == 0)

        if fixed:
            return True, f"Fixed docstrings in {file_path}"
        else:
            return False, f"No docstring issues to fix in {file_path}"

    except Exception as e:
        return False, f"Error processing {file_path}: {e}"


def process_path(path: Path) -> Tuple[int, List[str]]:
    """Process a file or recursively process a directory.

    Args:
        path: Path to a file or directory

    Returns:
        A tuple containing the number of files changed and a list of changed file paths

    """
    changes_count = 0
    changed_files = []

    if path.is_file() and path.suffix == ".py":
        fixed, message = fix_docstrings(path)
        if fixed:
            changes_count = 1
            changed_files = [str(path)]
    elif path.is_dir():
        for py_file in path.glob("**/*.py"):
            fixed, message = fix_docstrings(py_file)
            if fixed:
                changes_count += 1
                changed_files.append(str(py_file))

    return changes_count, changed_files


def main():
    """Parse command line arguments and run the script."""
    parser = argparse.ArgumentParser(
        description="Fix docstring formatting issues using Ruff"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=["."],
        help="Paths to files or directories to process",
    )
    args = parser.parse_args()

    total_changes = 0
    changed_files = []

    for path_str in args.paths:
        path = Path(path_str)
        if not path.exists():
            print(f"Path does not exist: {path}")
            continue

        changes, files = process_path(path)
        total_changes += changes
        changed_files.extend(files)

    print(f"Fixed docstrings in {total_changes} files")
    if total_changes > 0:
        print("Changed files:")
        for file_path in changed_files:
            print(f"  {file_path}")


if __name__ == "__main__":
    main()
