
# Refactored from: format_and_lint
# Date: 2025-03-16T16:19:08.208590
# Refactor Version: 1.0
# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:47:41 2025

"""Script to format and lint all Python code in the project.

This script provides automated code formatting and linting for the entire project
using Black (formatter) and Flake8 (linter). It processes all Python files in the
'scripts' and 'tests' directories.

The script handles:
- Formatting code according to PEP 8 standards using Black
- Checking code quality and style using Flake8
- Error handling and reporting for both tools
- Recursive directory traversal for Python files

Usage:
    python scripts/format_and_lint.py
"""

import subprocess
import sys
from pathlib import Path


def format_and_lint() -> None:
    """Format all Python files with Black and check with Flake8.

    This function performs the following operations:
    1. Finds all Python files in 'scripts' and 'tests' directories
    2. Formats each file using Black
    3. Runs Flake8 on all files to check for style violations
    4. Handles and reports any errors from both tools

    Raises
    ------
        SystemExit: If critical errors occur during processing

    """
    # Get all Python files in scripts and tests directories recursively
    python_files = list(Path("scripts").glob("**/*.py")) + list(
        Path("tests").glob("**/*.py"),
    )

    # Format files with Black
    for file in python_files:
        try:
            # Run black formatter on each file
            subprocess.run(["black", str(file)], check=True)
        except subprocess.CalledProcessError:
            # Handle formatting errors gracefully
            sys.exit(1)

    # Check code quality with Flake8
    try:
        # Run flake8 on all files in scripts and tests directories
        subprocess.run(["flake8", "scripts", "tests"], check=True)
    except subprocess.CalledProcessError:
        # Handle linting errors and provide feedback
        sys.exit(1)


if __name__ == "__main__":
    # Entry point for the script
    format_and_lint()
