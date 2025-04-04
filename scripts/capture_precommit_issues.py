#!/usr/bin/env python3
"""
Capture pre-commit hook output and append issues to TODO.md.

This script reads from stdin (where pre-commit output is piped),
extracts meaningful error information, and appends it to a dedicated
section in TODO.md.
"""

import argparse
import operator
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

# Default debug setting (can be overridden by command line)
DEBUG = False


def debug_log(message):
    """Print debug message with timestamp if DEBUG is enabled."""
    if DEBUG:
        elapsed = time.time() - debug_log.start_time
        print(f"[DEBUG] [{elapsed:.2f}s] {message}", file=sys.stderr)


# Initialize timer for debug logging
debug_log.start_time = time.time()


def strip_ansi(text):
    """Remove all ANSI escape sequences from text including colors, styles, etc."""
    debug_log(f"Stripping ANSI codes from {len(text) if text else 0} chars")
    # Comprehensive pattern that matches:
    # - CSI (Control Sequence Introducer) sequences \x1B[...
    # - OSC (Operating System Command) sequences \x1B]...
    # - Other escape sequences \x1B...
    ansi_escape = re.compile(
        r"""
        \x1B  # ESC
        (?:   # 7-bit C1 Fe (except CSI)
            [@-Z\\-_]
        |     # or [ for CSI
            \[
            [0-?]*  # Parameter bytes
            [ -/]*  # Intermediate bytes
            [@-~]   # Final byte
        |     # or ] for OSC
            \]
            [^\x07]*  # OSC string
            (?:\x07|$)  # ST (String Terminator) or end of string
        )
    """,
        re.VERBOSE,
    )

    # Handle additional color codes that might use different formats
    if not text:
        return ""

    # First pass with our comprehensive pattern
    clean_text = ansi_escape.sub("", text)

    # Second pass to catch any missed color codes with simpler pattern
    simple_ansi = re.compile(r"\033\[[0-9;]*[a-zA-Z]")
    clean_text = simple_ansi.sub("", clean_text)

    # Third pass for any remaining escape sequences including \u001b format
    remaining_ansi = re.compile(r"(\u001b|\x1b|\033)(\[.*?[@-~]|\].*?(\a|$))")
    clean_text = remaining_ansi.sub("", clean_text)

    # Fourth pass for bracketed color codes like [1;38;5;9m
    bracketed_colors = re.compile(r"\[[0-9;]+m")
    clean_text = bracketed_colors.sub("", clean_text)

    return clean_text


def run_linters():
    """Run linters and return their combined output without ANSI colors."""
    debug_log("Starting linter runs")
    output = []
    # Force no color output in the environment for all tools
    env = {
        **os.environ,
        "NO_COLOR": "1",
        "PY_COLORS": "0",
        "FORCE_COLOR": "0",
        "TERM": "dumb",  # Disable terminal capabilities
        "CLICOLOR": "0",
        "CLICOLOR_FORCE": "0",
    }

    # Run ruff without ANSI colors
    try:
        debug_log("Running ruff linter")
        start_time = time.time()
        # Try different command versions to ensure compatibility
        ruff_commands = [
            # Match the exact settings from .pre-commit-config.yaml
            [
                "ruff",
                "check",
                "--preview",
                "--select=ALL",
                "--ignore=E501,E203,D203,D212",
                "--no-fix",  # Important: we don't want to modify files here
                "--no-color",
                ".",
            ],
            # Fallback version with fewer options
            [
                "ruff",
                "check",
                "--select=ALL",
                "--ignore=E501,E203,D203,D212",
                "--no-fix",
                "--no-color",
                ".",
            ],
            # Minimal command for older versions
            [
                "ruff",
                "check",
                "--select=ALL",
                "--ignore=E501,E203,D203,D212",
                "--no-fix",
                ".",
            ],
        ]

        success = False
        for cmd in ruff_commands:
            try:
                debug_log(f"Trying ruff command: {' '.join(cmd)}")
                result = subprocess.run(
                    cmd, capture_output=True, text=True, check=False, env=env,
                )
                if (
                    result.returncode != 2
                ):  # Return code 2 indicates command error, not linting error
                    output.append(result.stdout)
                    if result.stderr and "unexpected argument" not in result.stderr:
                        output.append(f"Ruff errors:\n{result.stderr}")
                    success = True
                    break
            except Exception as e:
                debug_log(f"Error running ruff command: {e}")
                continue

        if not success:
            output.append("Failed to run ruff with any command variant")
        debug_log(f"Finished running ruff in {time.time() - start_time:.2f}s")
    except Exception as e:
        debug_log(f"Exception in ruff execution: {e}")
        output.append(f"Failed to run ruff: {e}")

    # Run pydocstyle
    try:
        debug_log("Running pydocstyle linter")
        start_time = time.time()
        # Try different command versions to ensure compatibility
        pydocstyle_commands = [
            # Match the settings from .pre-commit-config.yaml
            ["pydocstyle", "--ignore=D203", "--match=.*\\.py", "--no-color", "."],
            # Fallback without no-color flag
            ["pydocstyle", "--ignore=D203", "--match=.*\\.py", "."],
        ]

        success = False
        for cmd in pydocstyle_commands:
            try:
                debug_log(f"Trying pydocstyle command: {' '.join(cmd)}")
                result = subprocess.run(
                    cmd, capture_output=True, text=True, check=False, env=env,
                )
                if (
                    result.returncode != 2
                ):  # Return code 2 indicates command error, not linting error
                    output.append(result.stdout)
                    if result.stderr and "unexpected argument" not in result.stderr:
                        output.append(f"Pydocstyle errors:\n{result.stderr}")
                    success = True
                    break
            except Exception as e:
                debug_log(f"Error running pydocstyle command: {e}")
                continue

        if not success:
            output.append("Failed to run pydocstyle with any command variant")
        debug_log(f"Finished running pydocstyle in {time.time() - start_time:.2f}s")
    except Exception as e:
        debug_log(f"Exception in pydocstyle execution: {e}")
        output.append(f"Failed to run pydocstyle: {e}")

    combined_output = "\n".join(output)
    debug_log(f"Combined linter output: {len(combined_output)} characters")
    # Still strip ANSI codes as a final safety measure
    return strip_ansi(combined_output)


def extract_issues(output):
    """Extract actionable issues from pre-commit output."""
    debug_log("Starting issue extraction")
    start_time = time.time()

    if not output:
        debug_log("No output to process")
        return []

    # Clean output of all ANSI codes before any processing
    output = strip_ansi(output)
    if not output:
        debug_log("No output after ANSI stripping")
        return []

    # Organize issues by file path for better consolidation
    issues_by_file = {}
    hook_issues = []  # For issues not tied to specific files

    # Extract all code quality issues
    issue_patterns = [
        # Syntax errors and parsing failures
        (
            r"(?:error: |Syntax error in |Cannot parse: )([^:]+):(?:\d+:\d+: )?(Expected an indented block|invalid syntax|Cannot parse|[^\n]+)",
            "Syntax/parsing error: {2}",
        ),
        # Additional syntax error format
        (
            r"(\S+\.py):(\d+):(?:\d+:)? (?:error:|syntax error:) (.*)",
            "Syntax error: {3} (line {2})",
        ),
        # Ruff format (with code)
        (r"([^:]+):(\d+):\d+: ([A-Z]\d{3}) (.+)", "{3}: {4} (line {2})"),
        # Ruff format (without code)
        (r"([^:]+):(\d+):\d+: (.+)", "Issue: {3} (line {2})"),
        # Pydocstyle specific formats
        (
            r"([^:]+):(\d+) in (?:public )?(?:function|class|method) '[^']+':\n\s*(D\d{3} [^\n]+)",
            "Docstring: {3} (line {2})",
        ),
        (
            r"([^:]+):(\d+) in (?:public )?(?:function|class|method) '[^']+':\n\s*([^\n]+)",
            "Docstring: {3} (line {2})",
        ),
        # Docstring issues (from pydocstyle/ruff)
        (r"([^:]+):(\d+):\d+: (D\d{3} [^\n]+)", "Docstring: {3} (line {2})"),
        (r"([^:]+):(\d+):\d+: \[(D\d{3})\]([^\n]+)", "Docstring [{3}]: {4} (line {2})"),
        # Style/linting violations
        (r"([^:]+):(\d+):\d+: ([A-Z]\d{3} [^\n]+)", "Style: {3} (line {2})"),
        (r"([^:]+):(\d+):\d+: \[([A-Z]\d{3})\]([^\n]+)", "Style [{3}]: {4} (line {2})"),
        # General warnings
        (r"([^:]+):(\d+):\d+: warning: ([^\n]+)", "Warning: {3} (line {2})"),
        # Complex multiline error formats with line/column indicators
        (
            r"([^:]+):(\d+)(?::\d+)?:.*\n\s*\|.*\n\s*\|(.*?)\^\+* ([A-Z]\d{3}).*",
            "{4}: {3} (line {2})",
        ),
    ]

    debug_log(f"Applying {len(issue_patterns)} issue patterns")
    pattern_start = time.time()
    for idx, (pattern, message_format) in enumerate(issue_patterns):
        pattern_match_start = time.time()
        matches = list(re.compile(pattern, re.MULTILINE).finditer(output))
        debug_log(
            f"Pattern {idx + 1}: Found {len(matches)} matches in {time.time() - pattern_match_start:.2f}s",
        )

        for match in matches:
            # Get file path from group 1
            if match.group(1):
                file_path = match.group(1).strip()
                # Clean the file path to ensure it's properly formatted
                file_path = strip_ansi(file_path)

                if file_path not in issues_by_file:
                    issues_by_file[file_path] = []

                # Format the message with match groups and clean ANSI codes
                message = message_format
                for i, group in enumerate(match.groups(), 1):
                    if group:
                        clean_group = strip_ansi(group.strip())
                        message = message.replace(f"{{{i}}}", clean_group)

                issues_by_file[file_path].append(strip_ansi(message))
    debug_log(f"Applied all patterns in {time.time() - pattern_start:.2f}s")

    # Look for TRY400, BLE001 and similar patterns that have a specific format
    debug_log("Checking for common error codes")
    error_start = time.time()
    common_error_codes = [
        "TRY400",
        "BLE001",
        "G004",
        "TD002",
        "TD003",
        "TD004",
        "FIX002",
    ]
    for code in common_error_codes:
        code_pattern = re.compile(
            r"([^:]+):(\d+)(?::\d+)?:.*\n.*\|\s+([^\n]*" + code + "[^\n]*)",
            re.MULTILINE,
        )
        matches = list(code_pattern.finditer(output))
        debug_log(f"Code {code}: Found {len(matches)} matches")

        for match in matches:
            file_path = strip_ansi(match.group(1).strip())
            line_num = match.group(2)
            error_text = strip_ansi(match.group(3).strip())

            if file_path not in issues_by_file:
                issues_by_file[file_path] = []

            issues_by_file[file_path].append(f"Issue: {error_text} (line {line_num})")
    debug_log(f"Finished checking error codes in {time.time() - error_start:.2f}s")

    # Extract class and code structure issues
    debug_log("Checking for class and structure issues")
    class_start = time.time()
    class_issue_patterns = [
        # Missing method implementations
        (
            r"Class '([^']+)' inherits from 'BaseScript' but doesn't implement the required '([^']+)' method",
            "Class '{0}' needs to implement '{1}' method (required by BaseScript)",
        ),
        # Other class-related issues
        (
            r"Class '([^']+)' is missing (?:abstract )?method '([^']+)'",
            "Class '{0}' needs to implement '{1}' method",
        ),
        # Function/method issues
        (
            r"Function '([^']+)' is too complex \(([^)]+)\)",
            "Function '{0}' is too complex ({1}) - consider refactoring",
        ),
        # Variable naming issues
        (
            r"Variable '([^']+)' in ([^:]+):\d+ doesn't conform to ([^\n]+)",
            "Naming: Variable '{0}' doesn't conform to {2}",
        ),
    ]

    for line in output.split("\n"):
        line = strip_ansi(line)
        for pattern, message_format in class_issue_patterns:
            match = re.compile(pattern).search(line)
            if match:
                # Format the message with match groups and clean ANSI codes
                message = message_format
                for i, group in enumerate(match.groups(), 0):
                    clean_group = strip_ansi(group)
                    message = message.replace(f"{{{i}}}", clean_group)

                # Try to extract file path if mentioned
                file_path = None
                file_match = re.search(r"in ([^:]+):", line)
                if file_match:
                    file_path = strip_ansi(file_match.group(1).strip())

                if file_path:
                    if file_path not in issues_by_file:
                        issues_by_file[file_path] = []
                    issues_by_file[file_path].append(message)
                else:
                    hook_issues.append(f"{message} (in unknown file)")
                break  # Only process first matching pattern per line
    debug_log(f"Finished checking class issues in {time.time() - class_start:.2f}s")

    # Extract hook failures (excluding those that automatically fixed issues)
    debug_log("Checking for hook failures")
    hook_start = time.time()
    hook_failure_pattern = re.compile(
        r"([^\n.]+)\.+Failed\n([^.]+?)(?=\n[^\s]+\.\.\.|$)", re.DOTALL,
    )
    for match in hook_failure_pattern.finditer(output):
        hook_name = strip_ansi(match.group(1).strip())
        failure_details = strip_ansi(match.group(2).strip())

        # Skip hooks that fixed files (these aren't errors, just notifications)
        if (
            "files were modified" in failure_details
            or "fixing" in failure_details.lower()
        ):
            continue

        # Ensure we only add real failures
        if failure_details and not failure_details.lower().startswith("fixing"):
            # Look for file paths in the failure details
            file_match = re.search(
                r"([^\s:]+\.(py|js|json|yaml|yml|md|rst))", failure_details,
            )

            if file_match:
                file_path = strip_ansi(file_match.group(1).strip())
                if file_path not in issues_by_file:
                    issues_by_file[file_path] = []

                # Clean up the failure message and remove ANSI codes
                clean_msg = strip_ansi(failure_details.split("Fixing")[0].strip())
                clean_msg = re.sub(
                    r"^[-\s]*", "", clean_msg,
                )  # Remove leading dashes/spaces
                issues_by_file[file_path].append(
                    f"{strip_ansi(hook_name)} failure: {clean_msg}",
                )
            else:
                # Also check for class/method issues in hook failures
                class_match = re.search(
                    r"Class '([^']+)' (?:is missing|needs to implement)",
                    failure_details,
                )
                if class_match:
                    hook_issues.append(
                        f"Class '{strip_ansi(class_match.group(1))}' needs implementation (from {hook_name})",
                    )
                else:
                    # Fallback to generic hook failure
                    clean_msg = strip_ansi(failure_details.split("Fixing")[0].strip())
                    clean_msg = re.sub(r"^[-\s]*", "", clean_msg)
                    hook_issues.append(
                        f"Fix `{strip_ansi(hook_name)}` failure: {clean_msg}",
                    )
    debug_log(f"Finished checking hook failures in {time.time() - hook_start:.2f}s")

    # Convert the grouped issues to a flat list of TODO items
    debug_log("Building final issue list")
    format_start = time.time()
    issues = []

    # First add file-specific issues
    debug_log(f"Processing {len(issues_by_file)} files with issues")
    for file_path, file_issues in issues_by_file.items():
        clean_path = strip_ansi(file_path)
        # Verify file path exists - this helps quick_fix.py recognize it as a file
        if not os.path.exists(clean_path) and clean_path.endswith(".py"):
            # Try to find the file in the project
            if os.path.exists(os.path.join("app", clean_path)):
                clean_path = os.path.join("app", clean_path)
            elif os.path.exists(os.path.join("scripts", clean_path)):
                clean_path = os.path.join("scripts", clean_path)
            elif os.path.exists(os.path.join("tests", clean_path)):
                clean_path = os.path.join("tests", clean_path)

        # Remove duplicates while preserving order
        unique_issues = []
        seen = set()
        for issue in file_issues:
            clean_issue = strip_ansi(issue)
            if clean_issue not in seen:
                seen.add(clean_issue)
                unique_issues.append(clean_issue)

        if len(unique_issues) == 1:
            # Single issue for this file
            clean_issue = unique_issues[0]
            # Format specifically for quick_fix.py recognition
            if os.path.exists(clean_path):
                issues.append(f"- [ ] {clean_path}: {clean_issue}")
            else:
                issues.append(f"- [ ] Fix issue in `{clean_path}`: {clean_issue}")
        else:
            # Multiple issues for this file - list them together
            if os.path.exists(clean_path):
                issues.append(f"- [ ] Fix issues in {clean_path}:")
            else:
                issues.append(f"- [ ] Fix issues in `{clean_path}`:")
            for i, issue in enumerate(unique_issues, 1):
                issues.append(f"  - {issue}")

    # Then add hook issues (not tied to specific files)
    # Remove duplicates while preserving order
    debug_log(f"Processing {len(hook_issues)} hook issues")
    unique_hook_issues = []
    seen = set()
    for issue in hook_issues:
        clean_issue = strip_ansi(issue)
        if clean_issue not in seen:
            seen.add(clean_issue)
            unique_hook_issues.append(clean_issue)

    for issue in unique_hook_issues:
        # Format hook issues in a way quick_fix.py can understand
        if issue.startswith("Fix `"):
            # Keep original format for hook issues
            issues.append(f"- [ ] {issue}")
        elif "needs implementation" in issue:
            # Format class issues
            class_match = re.search(r"Class '([^']+)' needs implementation", issue)
            if class_match:
                class_name = class_match.group(1)
                issues.append(f"- [ ] Class `{class_name}` needs implementation")
            else:
                issues.append(f"- [ ] {issue}")
        else:
            # For other issues, wrap any identifiable parts in backticks
            # This helps quick_fix.py identify the hook
            for common_pattern in ["TRY400", "BLE001", "G004", "D213", "D100"]:
                if common_pattern in issue:
                    issue = issue.replace(common_pattern, f"`{common_pattern}`")
                    break
            issues.append(f"- [ ] {issue}")

    debug_log(f"Built final issue list in {time.time() - format_start:.2f}s")
    debug_log(
        f"Completed issue extraction in {time.time() - start_time:.2f}s, found {len(issues)} issues",
    )
    return issues


def consolidate_similar_issues(issues):
    """
    Consolidate similar issues to reduce duplication.

    Returns
    -------
        List of tuples (issue_text, count)

    """
    debug_log(f"Starting issue consolidation with {len(issues)} issues")
    start_time = time.time()

    # First pass: clean and normalize issues
    cleaned_issues = []
    for issue in issues:
        issue = strip_ansi(issue)

        # Skip empty or malformed issues
        if not issue or issue.isspace():
            continue

        cleaned_issues.append(issue)

    debug_log(f"Cleaned {len(cleaned_issues)} issues")

    # Exact duplicates
    issue_counts = {}
    for issue in cleaned_issues:
        if issue in issue_counts:
            issue_counts[issue] += 1
        else:
            issue_counts[issue] = 1

    debug_log(f"Found {len(issue_counts)} unique issues")

    # Second pass: consolidate similar patterns
    consolidated = {}

    # Patterns for classes that need to implement methods
    class_implement_pattern = re.compile(
        r"- \[ \] Class '([^']+)' needs to implement '([^']+)' method",
    )

    for issue, count in issue_counts.items():
        # Check for classes that need to implement methods
        class_match = class_implement_pattern.search(issue)
        if class_match:
            class_name = class_match.group(1)
            method_name = class_match.group(2)

            # If it's a common method like 'execute', consolidate by method
            if method_name == "execute":
                key = f"- [ ] Multiple classes need to implement '{method_name}' method"
                if key in consolidated:
                    consolidated[key] += count
                else:
                    consolidated[key] = count
                continue

        # If no patterns match, keep the original issue
        consolidated[issue] = count

    # Convert to list of tuples and sort by count (descending)
    result = sorted(consolidated.items(), key=operator.itemgetter(1), reverse=True)

    debug_log(
        f"Consolidated to {len(result)} unique issue patterns in {time.time() - start_time:.2f}s",
    )
    return result


def update_todo_file(issues, quiet=False):
    """Update TODO.md with pre-commit issues."""
    debug_log(f"Starting TODO.md update with {len(issues)} issues")
    start_time = time.time()

    if not issues:
        debug_log("No issues to update")
        if not quiet:
            print("No new issues detected by pre-commit.")
        # Optionally clear the existing section if no issues are found
        # clear_precommit_issues_section()
        return

    # Clean up any issues that are malformed due to parsing errors
    # This handles edge cases with complex error messages
    cleaned_issues = []
    for issue in issues:
        # Remove any malformed syntax error messages
        if "`{e}" in issue or "{e}" in issue:
            continue

        # Avoid any lines that still have pipe characters which might be from partial match
        if "| " in issue and (issue.strip()[0] == "|" or "    |" in issue):
            continue

        # Keep only valid issue lines
        cleaned_issues.append(issue)

    debug_log(
        f"Cleaned issues: {len(cleaned_issues)} (removed {len(issues) - len(cleaned_issues)})",
    )
    issues = cleaned_issues

    todo_path = "TODO.md"
    debug_log(f"Updating {todo_path}")

    # Create if it doesn't exist
    if not os.path.exists(todo_path):
        debug_log("Creating new TODO.md file")
        with open(todo_path, "w") as f:
            f.write("# Dewey Project - TODO List\n\n")

    # Read the current content
    debug_log("Reading current TODO.md content")
    read_start = time.time()
    with open(todo_path) as f:
        content = f.read()
    debug_log(f"Read {len(content)} bytes in {time.time() - read_start:.2f}s")

    # Define the section header and find its start
    section_header = "## Pre-commit Issues"
    start_index = content.find(section_header)
    debug_log(f"Found section at index {start_index}")

    # Prepare the new content for the section
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    section_header_with_timestamp = f"{section_header} (Last updated: {timestamp})"

    # Group and consolidate similar issues
    debug_log("Consolidating similar issues")
    consolidate_start = time.time()
    consolidated_issues = consolidate_similar_issues(issues)
    debug_log(
        f"Consolidated {len(issues)} issues to {len(consolidated_issues)} in {time.time() - consolidate_start:.2f}s",
    )

    # Group issues by type for better organization
    debug_log("Grouping issues by type")
    group_start = time.time()
    issue_groups = {
        "Syntax Errors": [],
        "Docstring Issues": [],
        "Style Violations": [],
        "Implementation Issues": [],
        "Other Issues": [],
    }

    for issue, count in consolidated_issues:
        # Add count indicator if there are duplicates
        issue_text = issue
        if count > 1:
            issue_text = f"{issue} ({count} instances)"

        if "Syntax" in issue or "parse" in issue:
            issue_groups["Syntax Errors"].append(issue_text)
        elif "Docstring" in issue or ("D" in issue and "Style" not in issue):
            issue_groups["Docstring Issues"].append(issue_text)
        elif "Style" in issue or any(code in issue for code in ["E", "F", "W"]):
            issue_groups["Style Violations"].append(issue_text)
        elif "implement" in issue or "Class" in issue:
            issue_groups["Implementation Issues"].append(issue_text)
        else:
            issue_groups["Other Issues"].append(issue_text)
    debug_log(f"Grouped issues in {time.time() - group_start:.2f}s")

    # Build the section content with organized groups
    debug_log("Building section content")
    format_start = time.time()
    new_section_content = []

    # Limit the number of issues displayed per category
    MAX_ISSUES_PER_CATEGORY = 20  # Adjust this value as needed

    for group_name, group_issues in issue_groups.items():
        if group_issues:
            group_name = strip_ansi(group_name)
            new_section_content.append(f"### {group_name}")

            # Sort issues by priority (those with count indicators first)
            sorted_issues = sorted(
                group_issues, key=lambda x: "instances" in x, reverse=True,
            )

            if len(sorted_issues) > MAX_ISSUES_PER_CATEGORY:
                # Display only the top issues and add a count for remaining
                displayed_issues = sorted_issues[:MAX_ISSUES_PER_CATEGORY]
                hidden_count = len(sorted_issues) - MAX_ISSUES_PER_CATEGORY

                new_section_content.extend(displayed_issues)
                new_section_content.append(
                    f"- [ ] *{hidden_count} more {group_name.lower()} not shown*",
                )
            else:
                new_section_content.extend(sorted_issues)

            new_section_content.append("")

    new_full_section = (
        f"{section_header_with_timestamp}\n\n"
        + "\n".join(new_section_content).strip()
        + "\n"
    )
    debug_log(f"Built section content in {time.time() - format_start:.2f}s")

    # Update the content
    debug_log("Updating final content")
    update_start = time.time()
    if start_index != -1:
        # Find the end of the section (next ## header or EOF)
        end_index_match = re.search(
            r"^## ", content[start_index + len(section_header) :], re.MULTILINE,
        )

        if end_index_match:
            end_index = start_index + len(section_header) + end_index_match.start()
            # Replace the existing section content
            # Ensure proper spacing if the section wasn't empty
            leading_content = content[:start_index]
            trailing_content = content[end_index:]
            new_content = f"{leading_content}{new_full_section}\n{trailing_content}"
        else:
            # Section is at the end of the file
            new_content = content[:start_index] + new_full_section
    else:
        # Section doesn't exist, append it
        new_content = content.rstrip() + "\n\n" + new_full_section

    # Ensure the final content is clean and ends with exactly one newline
    new_content = strip_ansi(new_content.rstrip()) + "\n"
    debug_log(f"Updated final content in {time.time() - update_start:.2f}s")

    # Atomically write the updated content
    debug_log("Writing updated content to file")
    write_start = time.time()
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, dir=os.path.dirname(todo_path),
        ) as temp_file:
            temp_file.write(new_content)
            temp_path = temp_file.name
        # Replace the original file
        shutil.move(temp_path, todo_path)
        debug_log(f"Wrote file in {time.time() - write_start:.2f}s")

        # Get total issue count
        total_issues = sum(count for _, count in consolidated_issues)
        if not quiet:
            print(
                f"Updated '{section_header}' section in {todo_path} with {total_issues} issues (consolidated to {len(consolidated_issues)} unique entries).",
            )
    except Exception as e:
        debug_log(f"Error writing file: {e}")
        if not quiet:
            print(f"Error writing to {todo_path}: {e}")
        # Clean up temp file if move failed
        if "temp_path" in locals() and os.path.exists(temp_path):
            os.remove(temp_path)

    # Output for users in terminal
    if not quiet:
        print("\nPre-commit found issues that need to be fixed:")
        for issue, count in consolidated_issues[:10]:  # Show only top 10 issues
            if count > 1:
                print(f"  {issue} ({count} instances)")
            else:
                print(f"  {issue}")

        if len(consolidated_issues) > 10:
            print(f"  ... and {len(consolidated_issues) - 10} more issues")

        print(
            f"\nThese issues have been added to {todo_path} in the '{section_header}' section.",
        )
        print("Run './scripts/quick_fix.py -a' to attempt automatic fixes.")

    debug_log(f"Completed TODO.md update in {time.time() - start_time:.2f}s")


def main():
    """Main function to run linters, process output and update TODO.md."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Capture pre-commit hook output and append issues to TODO.md",
    )
    parser.add_argument(
        "--debug", "-d", action="store_true", help="Enable debug logging",
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress normal output",
    )
    args = parser.parse_args()

    # Set global debug flag
    global DEBUG
    DEBUG = args.debug

    # Reset timer if debug is enabled
    if DEBUG:
        debug_log.start_time = time.time()

    debug_log("Starting script execution")
    overall_start = time.time()

    debug_log("Running linters")
    linter_start = time.time()
    output = run_linters()
    debug_log(f"Linters completed in {time.time() - linter_start:.2f}s")

    if not output:
        debug_log("No linting output generated")
        if not args.quiet:
            print("No linting output generated")
        return 1

    # Write output to file for debugging
    debug_log("Writing debug log")
    debug_path = Path("precommit_output.log")
    try:
        with debug_path.open("w") as f:
            f.write(output)
    except Exception as e:
        debug_log(f"Could not write debug log: {e}")
        if not args.quiet:
            print(f"Warning: Could not write debug log: {e}")

    debug_log("Extracting issues")
    extract_start = time.time()
    issues = extract_issues(output)
    debug_log(f"Issue extraction completed in {time.time() - extract_start:.2f}s")

    debug_log("Updating TODO.md")
    update_start = time.time()
    update_todo_file(issues, args.quiet)
    debug_log(f"TODO.md update completed in {time.time() - update_start:.2f}s")

    debug_log(f"Script execution completed in {time.time() - overall_start:.2f}s")
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
