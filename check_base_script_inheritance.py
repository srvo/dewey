#!/usr/bin/env python3
"""
Check and fix BaseScript inheritance in Python files.

This script:
1. Scans all Python files in the reorganized structure
2. Checks if non-test files properly inherit from BaseScript
3. Fixes files that don't inherit from BaseScript
4. Generates a report of files that need fixing

Usage:
    python check_base_script_inheritance.py [--fix] [--dry-run]

Options:
    --fix       Automatically fix files that don't inherit from BaseScript
    --dry-run   Run without making any file changes (just print what would happen)
"""

import os
import re
import sys
import argparse
import ast
import logging
import traceback
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("base_script_check.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Constants
SRC_DIR = "/Users/srvo/dewey/src"
BASE_SCRIPT_IMPORT = "from dewey.core.base_script import BaseScript"
BASE_SCRIPT_IMPORT_PATTERN = r"from\s+dewey\.core\.base_script\s+import\s+BaseScript"

# Lists of directories/files to exclude from checks
EXCLUDE_DIRS = [
    "tests", 
    "test",
    "__pycache__",
    ".git",
]

EXCLUDE_FILES = [
    "base_script.py",  # The base script itself
    "__init__.py",     # Init files don't need to inherit
    "setup.py",        # Setup files don't need to inherit
    "conftest.py",     # Test configuration files
]

def is_excluded(file_path: str) -> bool:
    """
    Check if a file should be excluded from BaseScript inheritance check.
    
    Args:
        file_path: Path to the file
        
    Returns:
        bool: True if the file should be excluded, False otherwise
    """
    # Skip files in excluded directories
    for excluded_dir in EXCLUDE_DIRS:
        if f"/{excluded_dir}/" in file_path:
            return True
    
    # Skip excluded file types
    filename = os.path.basename(file_path)
    if filename in EXCLUDE_FILES:
        return True
        
    # Skip test files
    if filename.startswith("test_") or filename.endswith("_test.py"):
        return True
        
    # Skip migration files
    if "migrations" in file_path or filename.startswith("migrate_"):
        return True
    
    return False

def find_python_files() -> List[str]:
    """
    Find all Python files in the source directory.
    
    Returns:
        List[str]: List of Python file paths
    """
    python_files = []
    for root, _, files in os.walk(SRC_DIR):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if not is_excluded(file_path):
                    python_files.append(file_path)
    
    logger.info(f"Found {len(python_files)} Python files to check")
    return python_files

def check_inheritance(file_path: str) -> Tuple[bool, bool, bool]:
    """
    Check if a file inherits from BaseScript.
    
    Args:
        file_path: Path to the Python file
        
    Returns:
        Tuple[bool, bool, bool]: 
            - Does the file import BaseScript?
            - Does the file inherit from BaseScript?
            - Does the file implement the run() method?
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if BaseScript is imported
        imports_base_script = bool(re.search(BASE_SCRIPT_IMPORT_PATTERN, content))
        
        # Parse AST to check inheritance and run method
        tree = ast.parse(content)
        
        inherits_base_script = False
        implements_run = False
        
        for node in ast.walk(tree):
            # Check for class definitions
            if isinstance(node, ast.ClassDef):
                # Check if class inherits from BaseScript
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == "BaseScript":
                        inherits_base_script = True
                
                # Check if class implements run method
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "run":
                        implements_run = True
        
        return imports_base_script, inherits_base_script, implements_run
        
    except Exception as e:
        logger.error(f"Error analyzing {file_path}: {str(e)}")
        return False, False, False

def fix_inheritance(file_path: str, dry_run: bool = False) -> bool:
    """
    Fix BaseScript inheritance in a Python file.
    
    Args:
        file_path: Path to the Python file
        dry_run: If True, don't actually modify the file
        
    Returns:
        bool: True if file was fixed or doesn't need fixing, False if error
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Skip files that are just config files or don't define classes
        if not re.search(r'class\s+\w+', content):
            logger.info(f"Skipping {file_path} - no class definitions found")
            return True
            
        # Check if BaseScript is already imported
        imports_base_script = bool(re.search(BASE_SCRIPT_IMPORT_PATTERN, content))
        
        # Update import if needed
        if not imports_base_script:
            # Find where to insert the import
            import_section_end = 0
            for match in re.finditer(r'^import|^from', content, re.MULTILINE):
                line_end = content.find('\n', match.start())
                if line_end > import_section_end:
                    import_section_end = line_end
            
            # If no imports found, add it at the top after docstring
            if import_section_end == 0:
                # Find end of docstring if exists
                docstring_match = re.search(r'^""".*?"""', content, re.DOTALL)
                if docstring_match:
                    import_section_end = docstring_match.end()
            
            # Insert the import
            content = (
                content[:import_section_end + 1] + 
                BASE_SCRIPT_IMPORT + "\n" + 
                content[import_section_end + 1:]
            )
        
        # Parse the modified content to find classes
        tree = ast.parse(content)
        class_nodes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        
        # Only modify the first class if it doesn't already inherit from BaseScript
        modified = False
        for class_node in class_nodes:
            # Skip classes that already inherit from BaseScript
            inherits_base_script = any(
                isinstance(base, ast.Name) and base.id == "BaseScript" 
                for base in class_node.bases
            )
            
            if not inherits_base_script:
                # Find the class definition in the source
                class_match = re.search(
                    fr'class\s+{class_node.name}\s*(\(.*?\))?\s*:', 
                    content
                )
                
                if class_match:
                    class_def = class_match.group(0)
                    
                    # Determine how to modify the class definition
                    if '(' in class_def:
                        # Already inherits from something, add BaseScript
                        new_class_def = class_def.replace('(', '(BaseScript, ', 1)
                    else:
                        # Doesn't inherit from anything, add BaseScript
                        new_class_def = class_def.replace(':', '(BaseScript):', 1)
                    
                    # Replace the class definition
                    content = content.replace(class_def, new_class_def, 1)
                    modified = True
                    break  # Only modify the first class
        
        # Check if class implements run method, add if missing
        if modified:
            # Check if run method exists
            run_method_exists = False
            for class_node in class_nodes:
                for item in class_node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "run":
                        run_method_exists = True
                        break
                if run_method_exists:
                    break
            
            # Add run method if missing
            if not run_method_exists:
                # Find the end of the class definition
                class_indent = "    "  # Default indentation
                for line in content.split('\n'):
                    if re.match(r'^\s*class\s+\w+', line):
                        class_indent = re.match(r'^(\s*)', line).group(1) + "    "
                
                run_method = f"\n{class_indent}def run(self) -> None:\n"
                run_method += f"{class_indent}    \"\"\"\n"
                run_method += f"{class_indent}    Run the script.\n"
                run_method += f"{class_indent}    \"\"\"\n"
                run_method += f"{class_indent}    # TODO: Implement script logic here\n"
                run_method += f"{class_indent}    raise NotImplementedError(\"The run method must be implemented\")\n"
                
                # Find where to insert run method - at end of class
                class_end = len(content)
                next_class = re.search(r'^\s*class\s+\w+', content, re.MULTILINE)
                if next_class:
                    class_end = next_class.start()
                
                # Insert run method
                content = content[:class_end] + run_method + content[class_end:]
        
        # Write changes back to file
        if modified and not dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Fixed BaseScript inheritance in {file_path}")
        elif modified:
            logger.info(f"[DRY RUN] Would fix BaseScript inheritance in {file_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error fixing {file_path}: {str(e)}")
        traceback.print_exc()
        return False

def analyze_files() -> Dict[str, List[str]]:
    """
    Analyze all Python files and categorize them.
    
    Returns:
        Dict[str, List[str]]: Dictionary of files by category
    """
    files_by_category = {
        "ok": [],  # Files that correctly inherit from BaseScript
        "missing_import": [],  # Files that need BaseScript import
        "missing_inheritance": [],  # Files that don't inherit from BaseScript
        "missing_run": [],  # Files that inherit but don't implement run()
        "errors": [],  # Files that had errors during analysis
    }
    
    python_files = find_python_files()
    for file_path in python_files:
        try:
            imports_base_script, inherits_base_script, implements_run = check_inheritance(file_path)
            
            if inherits_base_script and implements_run:
                files_by_category["ok"].append(file_path)
            elif not imports_base_script:
                files_by_category["missing_import"].append(file_path)
            elif not inherits_base_script:
                files_by_category["missing_inheritance"].append(file_path)
            elif not implements_run:
                files_by_category["missing_run"].append(file_path)
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {str(e)}")
            files_by_category["errors"].append(file_path)
    
    return files_by_category

def main():
    """Main function to check and fix BaseScript inheritance."""
    parser = argparse.ArgumentParser(description="Check and fix BaseScript inheritance in Python files.")
    parser.add_argument("--fix", action="store_true", help="Automatically fix files that don't inherit from BaseScript")
    parser.add_argument("--dry-run", action="store_true", help="Run without making any file changes")
    args = parser.parse_args()
    
    logger.info("Starting BaseScript inheritance check")
    
    # Analyze files
    files_by_category = analyze_files()
    
    # Print summary
    logger.info("\nSummary of file analysis:")
    logger.info(f"- {len(files_by_category['ok'])} files are correctly configured")
    logger.info(f"- {len(files_by_category['missing_import'])} files need BaseScript import")
    logger.info(f"- {len(files_by_category['missing_inheritance'])} files don't inherit from BaseScript")
    logger.info(f"- {len(files_by_category['missing_run'])} files don't implement required run() method")
    logger.info(f"- {len(files_by_category['errors'])} files had errors during analysis")
    
    # Fix files if requested
    if args.fix or args.dry_run:
        files_to_fix = (
            files_by_category["missing_import"] + 
            files_by_category["missing_inheritance"] + 
            files_by_category["missing_run"]
        )
        
        logger.info(f"\nAttempting to fix {len(files_to_fix)} files")
        fixed_count = 0
        
        for file_path in files_to_fix:
            if fix_inheritance(file_path, args.dry_run):
                fixed_count += 1
        
        if args.dry_run:
            logger.info(f"[DRY RUN] Would fix {fixed_count}/{len(files_to_fix)} files")
        else:
            logger.info(f"Fixed {fixed_count}/{len(files_to_fix)} files")
    
    # Exit with error code if there are issues
    if (len(files_by_category["missing_import"]) + 
        len(files_by_category["missing_inheritance"]) + 
        len(files_by_category["missing_run"]) + 
        len(files_by_category["errors"])) > 0:
        logger.warning("Some files may need manual attention")
        if not args.fix:
            logger.info("Run with --fix to automatically fix issues")
        sys.exit(1)
    else:
        logger.info("All files are correctly configured")
        sys.exit(0)

if __name__ == "__main__":
    main() 