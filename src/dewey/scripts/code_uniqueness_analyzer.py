#!/usr/bin/env python

import glob
import os
import re

def analyze_code_uniqueness(root_dir="src"):
    """
    Lists all files with the _xxxxxxxx pattern.

    Args:
        root_dir (str): The root directory to search for Python files.

    Returns:
        list: A list of legacy file paths.
    """

    legacy_files = []

    # Discover all Python files in the source directory
    for filename in glob.iglob(root_dir + '**/*.py', recursive=True):
        if filename.endswith(".py"):
            if re.search(r"_[0-9a-zA-Z]{8}", os.path.basename(filename)):
                legacy_files.append(filename)

    return legacy_files


def generate_report(legacy_files):
    """
    Generates a report listing the legacy files.

    Args:
        legacy_files (list): A list of legacy file paths.
    """
    print("Legacy Files Found:")
    print("===================")
    if legacy_files:
        for filename in legacy_files:
            print(f"- {filename}")
    else:
        print("No legacy files found.")


if __name__ == "__main__":
    legacy_files = analyze_code_uniqueness()
    generate_report(legacy_files)
