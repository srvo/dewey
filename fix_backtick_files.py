#!/usr/bin/env python
"""Fixes Python files by removing markdown code markers."""

import os
import re
import sys


def fix_python_file(file_path: str) -> bool:
    """
    Fixes a Python file by removing ```python and ``` markers.

    Args:
        file_path: The path to the Python file.

    Returns:
        True if the file was fixed, False otherwise.

    """
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    # Check if the file contains ```python
    if "```python" in content:
        # Remove ```python at the beginning and ``` at the end
        fixed_content = re.sub(r"^```python\n", "", content)
        fixed_content = re.sub(r"\n```\s*$", "", fixed_content)

        # Write the fixed content back to the file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(fixed_content)
        return True
    return False


def fix_files_in_directory(directory: str) -> int:
    """
    Fixes all Python files in a directory recursively.

    Args:
        directory: The directory to search.

    Returns:
        The number of files fixed.

    """
    fixed_count = 0
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                if fix_python_file(file_path):
                    fixed_count += 1

    return fixed_count


if __name__ == "__main__":
    directory = sys.argv[1] if len(sys.argv) > 1 else "src"

    fixed_count = fix_files_in_directory(directory)
