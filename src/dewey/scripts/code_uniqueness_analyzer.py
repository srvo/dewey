#!/usr/bin/env python

import glob
import os
import re
import difflib

def analyze_code_uniqueness(root_dir="src"):
    """
    Analyzes the codebase to identify files with the _xxxxxxxx pattern and
    determines the extent to which they contain logic not already present in
    other files using SequenceMatcher.

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
            if re.search(r"_[0-9a-zA-Z]{8}", os.path.basename(filename)):
                legacy_files.append(filename)
            else:
                current_files.append(filename)

    if not legacy_files:
        print("\nNo legacy files found matching the _xxxxxxxx pattern.")
        return {}

    results = {}

    for legacy_file in legacy_files:
        try:
            with open(legacy_file, 'r', encoding='utf-8') as f:
                legacy_content = f.read()
        except UnicodeDecodeError as e:
            print(f"Error reading file {legacy_file}: {e}")
            continue

        total_characters = len(legacy_content)
        matched_characters = 0

        for current_file in current_files:
            try:
                with open(current_file, 'r', encoding='utf-8') as cf:
                    current_content = cf.read()
            except UnicodeDecodeError as e:
                print(f"Error reading file {current_file}: {e}")
                continue

            # Use SequenceMatcher to find the best matching blocks
            matcher = difflib.SequenceMatcher(None, legacy_content, current_content)
            for block in matcher.get_matching_blocks():
                # Accumulate the number of matched characters
                matched_characters += block.size

        # Calculate uniqueness percentage based on matched characters
        uniqueness_percentage = (
            (total_characters - matched_characters) / total_characters
        ) * 100 if total_characters > 0 else 0

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
        print(f"- {filename}: {percentage:.2f}% unique characters")


if __name__ == "__main__":
    analysis_results = analyze_code_uniqueness()
    generate_report(analysis_results)
