#!/usr/bin/env python3
"""
Script to compare implementations between old_dewey and src directories,
identify files that need to be migrated or enhanced.
"""

import os
import sys
import ast
import difflib
import fnmatch
import logging
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Set, Optional, Tuple
import re
import argparse
import concurrent.futures

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Constants
OLD_CODEBASE = "/Users/srvo/dewey/old_dewey"
NEW_CODEBASE = "/Users/srvo/dewey/src"
MIGRATION_SCRIPTS_DIR = "migration_scripts"
REPORT_FILE = "codebase_comparison_report.txt"

# Files to ignore during comparison
IGNORE_PATTERNS = [
    "*.pyc",
    "*__pycache__*",
    ".git*",
    "*.egg-info",
    "*.DS_Store",
    "*.pytest_cache*",
    "*venv*",
    "*.idea*",
    "*.vscode*",
]


@dataclass
class FileReport:
    """Data class to hold comparison results for each file."""
    old_path: str
    new_path: str
    old_exists: bool
    new_exists: bool
    old_line_count: int = 0
    new_line_count: int = 0
    old_class_count: int = 0
    new_class_count: int = 0
    old_function_count: int = 0
    new_function_count: int = 0
    old_complexity: float = 0.0
    new_complexity: float = 0.0
    similarity: float = 0.0
    needs_migration: bool = False
    migration_recommendations: str = ""


def is_ignored(path: str) -> bool:
    """Check if a file should be ignored based on patterns."""
    for pattern in IGNORE_PATTERNS:
        if fnmatch.fnmatch(os.path.basename(path), pattern):
            return True
    return False


def find_python_files(directory: str) -> List[str]:
    """Find all Python files in the given directory."""
    python_files = []
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py") and not is_ignored(os.path.join(root, file)):
                python_files.append(os.path.join(root, file))
    
    return python_files


def get_relative_path(file_path: str, base_path: str) -> str:
    """Get the relative path from base path."""
    try:
        return os.path.relpath(file_path, base_path)
    except ValueError:
        # If paths are on different drives (Windows)
        return file_path


def calculate_similarity(old_content: str, new_content: str) -> float:
    """Calculate the similarity between two file contents."""
    if not old_content and not new_content:
        return 1.0  # Both empty
    if not old_content or not new_content:
        return 0.0  # One is empty
    
    sequence_matcher = difflib.SequenceMatcher(None, old_content, new_content)
    return sequence_matcher.ratio()


def count_classes_and_functions(content: str) -> Tuple[int, int]:
    """Count the number of classes and functions in Python code."""
    try:
        tree = ast.parse(content)
        classes = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
        functions = sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
        return classes, functions
    except SyntaxError:
        logging.warning("Syntax error parsing code")
        return 0, 0


def calculate_cyclomatic_complexity(content: str) -> float:
    """Calculate the cyclomatic complexity of Python code."""
    try:
        # Simple estimation based on control structures
        # A more accurate measurement would use tools like radon or mccabe
        tree = ast.parse(content)
        
        complexity = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.For, ast.While, ast.And, ast.Or)):
                complexity += 1
            elif isinstance(node, ast.FunctionDef):
                complexity += 1
        
        if complexity == 0:
            return 0.0
        
        # Normalize by lines of code
        lines = len(content.splitlines())
        if lines == 0:
            return 0.0
        
        return complexity / lines
    except SyntaxError:
        logging.warning("Syntax error calculating complexity")
        return 0.0


def analyze_file(file_path: str) -> Tuple[int, int, int, float]:
    """Analyze a file and return its metrics."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        line_count = len(content.splitlines())
        class_count, function_count = count_classes_and_functions(content)
        complexity = calculate_cyclomatic_complexity(content)
        
        return line_count, class_count, function_count, complexity
    except Exception as e:
        logging.error(f"Error analyzing file {file_path}: {e}")
        return 0, 0, 0, 0.0


def get_file_content(file_path: str) -> str:
    """Get the content of a file safely."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {e}")
        return ""


def compare_files(old_file: str, new_file: str) -> FileReport:
    """Compare two files and generate a report."""
    old_exists = os.path.exists(old_file)
    new_exists = os.path.exists(new_file)
    
    # Initialize report
    report = FileReport(
        old_path=old_file,
        new_path=new_file,
        old_exists=old_exists,
        new_exists=new_exists
    )
    
    # If neither file exists, return early
    if not old_exists and not new_exists:
        return report
    
    # Get content and metrics for old file
    if old_exists:
        old_content = get_file_content(old_file)
        report.old_line_count, report.old_class_count, report.old_function_count, report.old_complexity = analyze_file(old_file)
    else:
        old_content = ""
    
    # Get content and metrics for new file
    if new_exists:
        new_content = get_file_content(new_file)
        report.new_line_count, report.new_class_count, report.new_function_count, report.new_complexity = analyze_file(new_file)
    else:
        new_content = ""
    
    # Calculate similarity if both files exist
    if old_exists and new_exists:
        report.similarity = calculate_similarity(old_content, new_content)
    
    # Determine if migration is needed
    if old_exists and new_exists:
        # New file exists but has less functionality
        if (report.new_line_count < report.old_line_count * 0.7 or
            report.new_class_count < report.old_class_count or
            report.new_function_count < report.old_function_count) and \
           report.similarity < 0.8:
            report.needs_migration = True
            report.migration_recommendations += "New file has less functionality than old file. "
    elif old_exists and not new_exists:
        # Old file exists but new one doesn't
        report.needs_migration = True
        report.migration_recommendations += "File exists in old codebase but not in new codebase. "
    
    return report


def generate_migration_script(report: FileReport, script_dir: str) -> None:
    """Generate a migration script based on the file report."""
    if not report.needs_migration:
        return
    
    script_path = os.path.join(script_dir, f"{os.path.basename(report.old_path)}.py")
    
    try:
        os.makedirs(script_dir, exist_ok=True)
        
        old_content = get_file_content(report.old_path) if report.old_exists else ""
        new_content = get_file_content(report.new_path) if report.new_exists else ""
        
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(f"""#!/usr/bin/env python3
\"\"\"
Migration script for {os.path.basename(report.old_path)}
Generated by codebase_comparison.py
\"\"\"

import os
import shutil
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define file paths
OLD_FILE_PATH = "{report.old_path}"
NEW_FILE_PATH = "{report.new_path}"

def migrate():
    \"\"\"Perform the migration from old to new codebase.\"\"\"
    logger.info(f"Migrating {{OLD_FILE_PATH}} to {{NEW_FILE_PATH}}")
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(NEW_FILE_PATH), exist_ok=True)
    
    # Migration logic based on analysis
    {generate_migration_logic(report, old_content, new_content)}
    
    logger.info(f"Migration complete for {{os.path.basename(OLD_FILE_PATH)}}")

if __name__ == "__main__":
    migrate()
""")
        logging.info(f"Generated migration script: {script_path}")
    except Exception as e:
        logging.error(f"Error generating migration script for {report.old_path}: {e}")


def generate_migration_logic(report: FileReport, old_content: str, new_content: str) -> str:
    """Generate the migration logic part of the script."""
    if not report.new_exists:
        return f"""# New file doesn't exist, copy the old file
with open(OLD_FILE_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# Add BaseScript integration if applicable
if 'class ' in content and not 'BaseScript' in content:
    content = "from dewey.core.base_script import BaseScript\\n" + content
    # Replace class definitions to inherit from BaseScript
    import re
    content = re.sub(r'class\\s+(\\w+)\\((?!BaseScript)', r'class \\1(BaseScript', content)

with open(NEW_FILE_PATH, 'w', encoding='utf-8') as f:
    f.write(content)

logger.info(f"Created {{NEW_FILE_PATH}} based on {{OLD_FILE_PATH}}")"""
    elif report.similarity < 0.5:
        return f"""# Files are very different, but old file has more functionality
# Create a backup of the new file
backup_path = NEW_FILE_PATH + '.bak'
shutil.copy2(NEW_FILE_PATH, backup_path)
logger.info(f"Created backup at {{backup_path}}")

# Merge the files (simple approach)
with open(OLD_FILE_PATH, 'r', encoding='utf-8') as f:
    old_content = f.read()

with open(NEW_FILE_PATH, 'r', encoding='utf-8') as f:
    new_content = f.read()

# Append old content as comments for manual review
with open(NEW_FILE_PATH, 'w', encoding='utf-8') as f:
    f.write(new_content)
    f.write("\\n\\n# ========= Content from old implementation for reference =========\\n")
    f.write("# " + old_content.replace('\\n', '\\n# '))

logger.info(f"Merged content from {{OLD_FILE_PATH}} to {{NEW_FILE_PATH}} for manual review")"""
    else:
        return f"""# Files are somewhat similar, extract additional functionality from old file
# Here you would implement a more sophisticated merging strategy
# For now, we'll just make a backup and print comparison info

# Create a backup of the new file
backup_path = NEW_FILE_PATH + '.bak'
shutil.copy2(NEW_FILE_PATH, backup_path)
logger.info(f"Created backup at {{backup_path}}")

# Display comparison info for manual review
print("Comparison:")
print(f"  Old file: {report.old_line_count} lines, {report.old_function_count} functions, {report.old_class_count} classes")
print(f"  New file: {report.new_line_count} lines, {report.new_function_count} functions, {report.new_class_count} classes")
print(f"  Similarity: {report.similarity:.2f}")

logger.info(f"Comparison info generated for manual review")"""


def generate_report(reports: List[FileReport], output_file: str) -> None:
    """Generate a comprehensive report of the comparison."""
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# Codebase Comparison Report\n\n")
            
            f.write("## Summary\n\n")
            total_files = len(reports)
            migration_needed = sum(1 for r in reports if r.needs_migration)
            
            f.write(f"- Total files compared: {total_files}\n")
            f.write(f"- Files recommended for migration: {migration_needed}\n\n")
            
            if migration_needed > 0:
                f.write("## Files Needing Migration\n\n")
                
                for report in reports:
                    if report.needs_migration:
                        rel_old_path = get_relative_path(report.old_path, OLD_CODEBASE)
                        rel_new_path = get_relative_path(report.new_path, NEW_CODEBASE) if report.new_exists else "N/A"
                        
                        f.write(f"### {os.path.basename(report.old_path)}\n\n")
                        f.write(f"- Old path: `{rel_old_path}`\n")
                        f.write(f"- New path: `{rel_new_path}`\n")
                        f.write(f"- Old lines: {report.old_line_count}\n")
                        f.write(f"- New lines: {report.new_line_count}\n")
                        f.write(f"- Old classes: {report.old_class_count}\n")
                        f.write(f"- New classes: {report.new_class_count}\n")
                        f.write(f"- Old functions: {report.old_function_count}\n")
                        f.write(f"- New functions: {report.new_function_count}\n")
                        f.write(f"- Similarity: {report.similarity:.2f}\n")
                        f.write(f"- Recommendations: {report.migration_recommendations}\n\n")
            
            f.write("## Files with Equivalent or Enhanced Implementation\n\n")
            for report in reports:
                if not report.needs_migration and report.old_exists and report.new_exists:
                    rel_old_path = get_relative_path(report.old_path, OLD_CODEBASE)
                    rel_new_path = get_relative_path(report.new_path, NEW_CODEBASE)
                    
                    f.write(f"### {os.path.basename(report.old_path)}\n\n")
                    f.write(f"- Old path: `{rel_old_path}`\n")
                    f.write(f"- New path: `{rel_new_path}`\n")
                    f.write(f"- Similarity: {report.similarity:.2f}\n\n")
            
            f.write("## New Files (Not in Old Codebase)\n\n")
            for report in reports:
                if not report.old_exists and report.new_exists:
                    rel_new_path = get_relative_path(report.new_path, NEW_CODEBASE)
                    
                    f.write(f"### {os.path.basename(report.new_path)}\n\n")
                    f.write(f"- Path: `{rel_new_path}`\n")
                    f.write(f"- Lines: {report.new_line_count}\n")
                    f.write(f"- Classes: {report.new_class_count}\n")
                    f.write(f"- Functions: {report.new_function_count}\n\n")
        
        logging.info(f"Report generated: {output_file}")
    except Exception as e:
        logging.error(f"Error generating report: {e}")


def compare_codebases(
    old_base: str, 
    new_base: str, 
    report_file: str, 
    migration_dir: str,
    output_type: str = "text"
) -> List[FileReport]:
    """Compare two codebases and generate reports and migration scripts."""
    # Find all Python files in both codebases
    old_files = find_python_files(old_base)
    new_files = find_python_files(new_base)
    
    # Map files by their relative paths
    old_relative_paths = {get_relative_path(f, old_base): f for f in old_files}
    new_relative_paths = {get_relative_path(f, new_base): f for f in new_files}
    
    # All unique relative paths
    all_relative_paths = set(old_relative_paths.keys()) | set(new_relative_paths.keys())
    
    # Prepare for comparison
    reports = []
    
    # Process each unique path
    for rel_path in all_relative_paths:
        old_file = old_relative_paths.get(rel_path, "")
        new_file = new_relative_paths.get(rel_path, "")
        
        # If the new file doesn't exist, construct the expected path
        if not new_file and old_file:
            new_file = os.path.join(new_base, rel_path)
        
        # If the old file doesn't exist, construct the expected path
        if not old_file and new_file:
            old_file = os.path.join(old_base, rel_path)
        
        # Compare the files
        report = compare_files(old_file, new_file)
        reports.append(report)
        
        # Generate migration script if needed
        if report.needs_migration:
            generate_migration_script(report, migration_dir)
    
    # Generate a comprehensive report
    generate_report(reports, report_file)
    
    # Log summary
    logging.info(f"Comparison completed:")
    logging.info(f"  Total files compared: {len(reports)}")
    logging.info(f"  Files recommended for migration: {sum(1 for r in reports if r.needs_migration)}")
    logging.info(f"  Report: {report_file}")
    logging.info(f"  Migration scripts: {migration_dir}/")
    
    return reports


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Compare two codebases and generate migration scripts.")
    parser.add_argument("--old", default=OLD_CODEBASE, help="Path to the old codebase.")
    parser.add_argument("--new", default=NEW_CODEBASE, help="Path to the new codebase.")
    parser.add_argument("--report", default=REPORT_FILE, help="Path to the output report file.")
    parser.add_argument("--migration-dir", default=MIGRATION_SCRIPTS_DIR, help="Directory for migration scripts.")
    parser.add_argument("--output-type", default="text", choices=["text", "json"], help="Output format.")
    args = parser.parse_args()
    
    compare_codebases(args.old, args.new, args.report, args.migration_dir, args.output_type)
    
    print(f"\nCodebase Comparison Summary:")
    print(f"  Total files compared: {len(find_python_files(args.old)) + len(find_python_files(args.new))}")
    print(f"  Files recommended for migration: {len([f for f in os.listdir(args.migration_dir) if f.endswith('.py')]) if os.path.exists(args.migration_dir) else 0}")
    print(f"\nFull report: {args.report}")
    print(f"Migration scripts: {args.migration_dir}/")


if __name__ == "__main__":
    main() 