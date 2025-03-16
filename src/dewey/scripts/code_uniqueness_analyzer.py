#!/usr/bin/env python

import glob
import os
import re
import difflib

def analyze_code_uniqueness(root_dir="src"):
    """
    Analyzes the codebase to identify files with the _xxxxxxxx pattern and
    determines the extent to which they contain logic not already present in
    other files.

    Args:
        root_dir (str): The root directory to search for Python files.

    Returns:
        dict: A dictionary where keys are legacy file paths and values are the
              percentage of unique lines in each file.
    """

    legacy_files = []
    current_files = []

    # Discover all Python files in the source directory
    for filename in glob.iglob(root_dir + '**/*.py', recursive=True):
        if filename.endswith(".py"):
            if re.match(r".*_[0-9a-f]{8}\.py$", filename):
                legacy_files.append(filename)
            else:
                current_files.append(filename)

    print("Legacy files found:")
    for file in legacy_files:
        print(f"- {file}")

    print("\nCurrent files found:")
    for file in current_files:
        print(f"- {file}")

    if not legacy_files:
        print("\nNo legacy files found matching the _xxxxxxxx pattern.")
        return {}

    results = {}

    for legacy_file in legacy_files:
        with open(legacy_file, 'r', encoding='utf-8') as f:
            legacy_lines = f.readlines()

        total_lines = len(legacy_lines)
        unique_lines = 0

        for i, legacy_line in enumerate(legacy_lines):
            found = False
            for current_file in current_files:
                with open(current_file, 'r', encoding='utf-8') as cf:
                    current_lines = cf.readlines()
                    if legacy_line in current_lines:
                        found = True
                        break
            if not found:
                unique_lines += 1

        uniqueness_percentage = (unique_lines / total_lines) * 100 if total_lines > 0 else 0
        results[legacy_file] = uniqueness_percentage

    return results


def generate_report(results):
    """
    Generates a report summarizing the code uniqueness analysis.

    Args:
        results (dict): A dictionary where keys are legacy file paths and
                        values are the percentage of unique lines.
    """
    print("Code Uniqueness Analysis Report:")
    print("================================")
    for filename, percentage in results.items():
        print(f"- {filename}: {percentage:.2f}% unique lines")


if __name__ == "__main__":
    analysis_results = analyze_code_uniqueness()
    generate_report(analysis_results)
