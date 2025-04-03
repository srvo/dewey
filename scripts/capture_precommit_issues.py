#!/usr/bin/env python3
"""Capture pre-commit hook output and append issues to TODO.md.

This script reads from stdin (where pre-commit output is piped),
extracts meaningful error information, and appends it to a dedicated
section in TODO.md.
"""

import sys
import os
import re
from datetime import datetime
import tempfile
import shutil


def read_precommit_output():
    """Read pre-commit output from stdin."""
    if sys.stdin.isatty():
        print(
            "Error: No input piped to script. This should be run as part of pre-commit."
        )
        return None

    return sys.stdin.read()


def extract_issues(output):
    """Extract actionable issues from pre-commit output."""
    if not output:
        return []

    # Organize issues by file path for better consolidation
    issues_by_file = {}
    hook_issues = []  # For issues not tied to specific files

    # Extract syntax errors
    syntax_error_pattern = re.compile(
        r"(?:error: |Syntax error in )([^:]+):[^:]+: (Expected an indented block|[^\n]+)"
    )
    for match in syntax_error_pattern.finditer(output):
        file_path = match.group(1).strip()
        error_msg = match.group(2).strip()

        if file_path not in issues_by_file:
            issues_by_file[file_path] = []

        issues_by_file[file_path].append(f"Syntax error: {error_msg}")

    # Extract class issues (missing execute methods)
    class_issue_pattern = re.compile(
        r"Class '([^']+)' inherits from 'BaseScript' but doesn't implement the required '([^']+)' method"
    )
    class_file_pattern = re.compile(r"in ([^:]+):")

    for line in output.split("\n"):
        class_match = class_issue_pattern.search(line)
        if class_match:
            class_name = class_match.group(1).strip()
            method_name = class_match.group(2).strip()

            # Try to extract file path if it's mentioned in the same line or nearby
            file_path = None
            file_match = class_file_pattern.search(line)

            if file_match:
                file_path = file_match.group(1).strip()

            if file_path:
                if file_path not in issues_by_file:
                    issues_by_file[file_path] = []

                issues_by_file[file_path].append(
                    f"Class '{class_name}' needs to implement '{method_name}' method (required by BaseScript)"
                )
            else:
                hook_issues.append(
                    f"Class '{class_name}' needs to implement '{method_name}' method (in unknown file)"
                )

    # Extract hook failures (excluding those that automatically fixed issues)
    hook_failure_pattern = re.compile(
        r"([^\n.]+)\.+Failed\n([^.]+?)(?=\n[^\s]+\.\.\.|$)", re.DOTALL
    )
    for match in hook_failure_pattern.finditer(output):
        hook_name = match.group(1).strip()
        failure_details = match.group(2).strip()

        # Skip hooks that fixed files (these aren't errors, just notifications)
        if "files were modified" in failure_details:
            continue

        # Ensure we only add real failures
        if failure_details and not failure_details.startswith("Fixing"):
            # Look for file paths in the failure details
            file_match = re.search(
                r"([^\s:]+\.(py|js|json|yaml|yml|md))", failure_details
            )

            if file_match:
                file_path = file_match.group(1).strip()
                if file_path not in issues_by_file:
                    issues_by_file[file_path] = []

                issues_by_file[file_path].append(
                    f"{hook_name} failure: {failure_details.split('Fixing')[0].strip()}"
                )
            else:
                hook_issues.append(
                    f"Fix `{hook_name}` failure: {failure_details.split('Fixing')[0].strip()}"
                )

    # Convert the grouped issues to a flat list of TODO items
    issues = []

    # First add file-specific issues
    for file_path, file_issues in issues_by_file.items():
        if len(file_issues) == 1:
            # Single issue for this file
            issues.append(f"- [ ] Fix issue in `{file_path}`: {file_issues[0]}")
        else:
            # Multiple issues for this file - list them together
            issues.append(f"- [ ] Fix issues in `{file_path}`:")
            for i, issue in enumerate(file_issues, 1):
                issues.append(f"  - {issue}")

    # Then add hook issues (not tied to specific files)
    for issue in hook_issues:
        issues.append(f"- [ ] {issue}")

    return issues


def update_todo_file(issues):
    """Update TODO.md with pre-commit issues."""
    if not issues:
        print("No new issues detected by pre-commit.")
        # Optionally clear the existing section if no issues are found
        # clear_precommit_issues_section()
        return

    todo_path = "TODO.md"

    # Create if it doesn't exist
    if not os.path.exists(todo_path):
        with open(todo_path, "w") as f:
            f.write("# Dewey Project - TODO List\\n\\n")

    # Read the current content
    with open(todo_path, "r") as f:
        content = f.read()

    # Define the section header and find its start
    section_header = "## Pre-commit Issues"
    start_index = content.find(section_header)

    # Prepare the new content for the section
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    section_header_with_timestamp = f"{section_header} (Last updated: {timestamp})"
    new_section_content = "\\n".join(issues)
    new_full_section = f"{section_header_with_timestamp}\\n\\n{new_section_content}\\n"

    if start_index != -1:
        # Find the end of the section (next ## header or EOF)
        end_index_match = re.search(
            r"^## ", content[start_index + len(section_header) :], re.MULTILINE
        )

        if end_index_match:
            end_index = start_index + len(section_header) + end_index_match.start()
            # Replace the existing section content
            # Ensure proper spacing if the section wasn't empty
            leading_content = content[:start_index]
            trailing_content = content[end_index:]
            new_content = f"{leading_content}{new_full_section}\\n{trailing_content}"  # Add extra newline for separation
        else:
            # Section is at the end of the file
            new_content = content[:start_index] + new_full_section
    else:
        # Section doesn't exist, append it
        new_content = content.rstrip() + "\\n\\n" + new_full_section

    # Ensure the final content ends with exactly one newline
    new_content = new_content.rstrip() + "\n"

    # Atomically write the updated content
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, dir=os.path.dirname(todo_path)
        ) as temp_file:
            temp_file.write(new_content)
            temp_path = temp_file.name
        # Replace the original file
        shutil.move(temp_path, todo_path)
        print(
            f"Updated '{section_header}' section in {todo_path} with {len(issues)} issues."
        )
    except Exception as e:
        print(f"Error writing to {todo_path}: {e}")
        # Clean up temp file if move failed
        if "temp_path" in locals() and os.path.exists(temp_path):
            os.remove(temp_path)

    # Output for users in terminal (unchanged)
    print("\\nPre-commit found issues that need to be fixed:")
    for issue in issues:
        print(f"  {issue}")
    print(
        f"\\nThese issues have been added to {todo_path} in the '{section_header}' section."
    )
    print("Run './scripts/quick_fix.py -a' to attempt automatic fixes.")


def main():
    """Main function to process pre-commit output and update TODO.md."""
    output = read_precommit_output()
    if not output:
        return 1

    issues = extract_issues(output)
    update_todo_file(issues)

    # Always exit with success (0) to let pre-commit continue
    # The actual errors will still be shown by pre-commit
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
