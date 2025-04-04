#!/usr/bin/env python3
"""
Code Quality Tool - Runs flake8 and black on Python files in specified directories.
Automatically formats code with black and reports on any remaining flake8 issues.
"""

import argparse
import logging
import operator
import os
import subprocess
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("code_quality")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run flake8 and black on Python files in a directory.",
    )
    parser.add_argument(
        "--dir",
        "-d",
        type=str,
        required=True,
        help="Directory containing Python files to process",
    )
    parser.add_argument(
        "--max-line-length",
        type=int,
        default=88,
        help="Maximum line length for flake8 (default: 88, matching black's default)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=os.cpu_count() or 1,
        help="Number of worker processes for parallel execution",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check for issues without making changes",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output",
    )
    return parser.parse_args()


def find_python_files(directory: Path) -> list[Path]:
    """Find all Python files in the given directory or return the file if it's a Python file."""
    if not directory.exists():
        logger.error(f"Path does not exist: {directory}")
        sys.exit(1)

    python_files = []
    if directory.is_file() and directory.suffix == ".py":
        python_files = [directory]
        logger.info(f"Processing single Python file: {directory}")
    else:
        if not directory.is_dir():
            logger.error(f"Path is not a directory or Python file: {directory}")
            sys.exit(1)
        python_files = list(directory.glob("**/*.py"))
        logger.info(f"Found {len(python_files)} Python files in {directory}")

    return python_files


def run_flake8(file_path: Path, max_line_length: int) -> tuple[Path, list[str]]:
    """Run flake8 on a file and return any issues."""
    try:
        cmd = ["flake8", str(file_path), f"--max-line-length={max_line_length}"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        issues = result.stdout.strip().split("\n") if result.stdout else []
        if issues == [""]:
            issues = []
        return file_path, issues
    except Exception as e:
        logger.error(f"Error running flake8 on {file_path}: {e}")
        return file_path, [f"Error: {e}"]


def run_black(file_path: Path, check_only: bool) -> tuple[Path, bool, str]:
    """Run black on a file and return whether it was formatted."""
    try:
        cmd = ["black"]
        if check_only:
            cmd.append("--check")
        cmd.append(str(file_path))

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        was_formatted = result.returncode == 0
        if not check_only and not was_formatted:
            was_formatted = "reformatted" in result.stderr

        return (file_path, was_formatted, result.stderr or result.stdout)
    except Exception as e:
        logger.error(f"Error running black on {file_path}: {e}")
        return file_path, False, f"Error: {e}"


def process_file(
    file_path: Path, check_only: bool, max_line_length: int, verbose: bool,
) -> dict:
    """Process a file with flake8 and black."""
    result = {
        "file": file_path,
        "formatted": False,
        "issues_before": [],
        "issues_after": [],
    }

    # First get initial flake8 issues
    _, initial_issues = run_flake8(file_path, max_line_length)
    result["issues_before"] = initial_issues

    # Run black to format
    _, was_formatted, black_output = run_black(file_path, check_only)
    result["formatted"] = was_formatted

    if verbose and black_output:
        logger.info(f"Black output for {file_path}:\n{black_output}")

    # Check flake8 again after formatting
    if not check_only:
        _, remaining_issues = run_flake8(file_path, max_line_length)
        result["issues_after"] = remaining_issues
    else:
        result["issues_after"] = initial_issues

    return result


def format_issue_count(issues: list[str]) -> dict:
    """Count issues by error code."""
    counts = {}
    for issue in issues:
        if not issue:
            continue
        try:
            parts = issue.split(":")
            if len(parts) >= 4:
                code = parts[3].strip().split()[0]
                counts[code] = counts.get(code, 0) + 1
        except Exception:
            pass
    return counts


def main() -> None:
    """Run the main program."""
    args = parse_args()
    directory = Path(args.dir)

    logger.info(f"Processing Python files in {directory}")
    logger.info(f"Using max line length: {args.max_line_length}")
    logger.info(f"Mode: {'Check only' if args.check_only else 'Fix'}")

    python_files = find_python_files(directory)

    if not python_files:
        logger.warning(f"No Python files found in {directory}")
        return

    # Check if flake8 and black are installed
    try:
        subprocess.run(["flake8", "--version"], capture_output=True, check=True)
        subprocess.run(["black", "--version"], capture_output=True, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.error(
            "flake8 and/or black are not installed. Please install them first.",
        )
        sys.exit(1)

    # Run black on the Python files
    black_issues = {}
    flake8_issues = {}

    results = []
    for file_path in python_files:
        logger.info(f"Processing {file_path}")
        result = process_file(
            file_path, args.check_only, args.max_line_length, args.verbose,
        )
        results.append(result)

    # Summarize results
    formatted_count = sum(1 for r in results if r.get("formatted", False))
    files_with_issues_before = sum(1 for r in results if r.get("issues_before", []))
    files_with_issues_after = sum(1 for r in results if r.get("issues_after", []))
    total_issues_before = sum(len(r.get("issues_before", [])) for r in results)
    total_issues_after = sum(len(r.get("issues_after", [])) for r in results)

    # Aggregate issues by type
    issues_before_by_code = {}
    issues_after_by_code = {}
    for r in results:
        for code, count in format_issue_count(r.get("issues_before", [])).items():
            issues_before_by_code[code] = issues_before_by_code.get(code, 0) + count
        for code, count in format_issue_count(r.get("issues_after", [])).items():
            issues_after_by_code[code] = issues_after_by_code.get(code, 0) + count

    # Print summary
    print("\n" + "=" * 70)
    print(f"CODE QUALITY SUMMARY FOR {directory}")
    print("=" * 70)
    print(f"Total Python files processed: {len(python_files)}")
    print(f"Files reformatted by black: {formatted_count}")
    print(
        f"Files with issues before: {files_with_issues_before} ({total_issues_before} issues)",
    )
    print(
        f"Files with issues after: {files_with_issues_after} ({total_issues_after} issues)",
    )
    print(f"Issues fixed: {total_issues_before - total_issues_after}")

    if args.verbose:
        print("\nIssues by type before formatting:")
        for code, count in sorted(
            issues_before_by_code.items(), key=operator.itemgetter(1), reverse=True,
        ):
            print(f"  {code}: {count}")

        print("\nIssues by type after formatting:")
        for code, count in sorted(
            issues_after_by_code.items(), key=operator.itemgetter(1), reverse=True,
        ):
            print(f"  {code}: {count}")

    # List files that still have issues
    if files_with_issues_after > 0:
        print("\nFiles with remaining issues:")
        for r in results:
            if r.get("issues_after", []):
                print(f"  {r['file']} ({len(r.get('issues_after', []))} issues)")
                if args.verbose:
                    for issue in r.get("issues_after", [])[
                        :5
                    ]:  # Show first 5 issues only
                        print(f"    {issue}")
                    if len(r.get("issues_after", [])) > 5:
                        print(
                            f"    ... and {len(r.get('issues_after', [])) - 5} more issues",
                        )

    print("\nRecommended fixes for common issues:")
    print("  E501 (line too long): Break long lines or use string continuation")
    print("  F401 (imported but unused): Remove unused imports")
    print("  E722 (bare except): Use specific exception types")
    print("  F841 (local variable never used): Remove unused variables")
    print("=" * 70)


if __name__ == "__main__":
    main()
