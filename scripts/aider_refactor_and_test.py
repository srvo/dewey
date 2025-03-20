#!/usr/bin/env python3
"""
Enhanced script for refactoring code and generating tests using Aider.

This script provides a comprehensive workflow to:
1. Refactor a given directory of Python files to match Dewey conventions
2. Generate comprehensive unit tests for the refactored files
"""

import argparse
import logging
from pathlib import Path
import os
import sys

from aider.coders import Coder
from aider.models import Model
from aider.io import InputOutput

PROJECT_ROOT = Path("/Users/srvo/dewey")
SRC_DIR = PROJECT_ROOT / "src"
CONVENTIONS_FILE = PROJECT_ROOT / "input_data/md_files/conventions.md"
CONFIG_FILE = PROJECT_ROOT / "config/dewey.yaml"
BASE_SCRIPT_FILE = PROJECT_ROOT / "src/dewey/core/base_script.py"
DB_UTILS_PATH = PROJECT_ROOT / "src/dewey/core/db"
LLM_UTILS_PATH = PROJECT_ROOT / "src/dewey/llm/llm_utils.py"
DEFAULT_MODEL = "deepinfra/google/gemini-2.0-flash-001"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("aider_refactor_and_test")

def read_file(file_path: Path) -> str:
    """Read a file and return its contents.
    
    Args:
        file_path: Path to the file to read
        
    Returns:
        The content of the file or empty string if file doesn't exist
    """
    try:
        with open(file_path, "r") as f:
            return f.read()
    except Exception as e:
        logger.warning(f"Could not read file {file_path}: {str(e)}")
        return ""

def read_conventions() -> str:
    """Read the conventions.md file for context.
    
    Returns:
        The content of the conventions.md file
    """
    return read_file(CONVENTIONS_FILE)

def read_config() -> str:
    """Read the dewey.yaml config file for context.
    
    Returns:
        The content of the config file
    """
    return read_file(CONFIG_FILE)

def read_base_script() -> str:
    """Read the base_script.py file for context.
    
    Returns:
        The content of the base_script.py file
    """
    return read_file(BASE_SCRIPT_FILE)

def find_python_files(path: Path) -> list[Path]:
    """Find all Python files in the directory or return the given file if it's a Python file.
    
    Args:
        path: Path to a directory or a Python file
        
    Returns:
        List of paths to Python files
    """
    if path.is_file() and path.suffix == '.py':
        return [path]
    elif path.is_dir():
        return list(path.glob("**/*.py"))
    return []

def find_test_files(path: Path) -> list[Path]:
    """Find all test files in the directory.
    
    Args:
        path: Path to a directory
        
    Returns:
        List of paths to test files
    """
    if path.is_dir():
        return list(path.glob("**/test_*.py"))
    return []

def build_refactor_prompt(conventions_content: str, config_content: str, base_script_content: str) -> str:
    """Build the refactor prompt with all context.
    
    Args:
        conventions_content: The content of the conventions.md file
        config_content: The content of the dewey.yaml file
        base_script_content: The content of the base_script.py file
        
    Returns:
        The complete refactor prompt with context
    """
    return f"""
Refactor this script to properly implement Dewey conventions:
1. Inherit from BaseScript with appropriate __init__ parameters
2. Implement run() method containing core logic
3. Use self.logger instead of print/logging
4. Access config via self.get_config_value() instead of hardcoded variables
5. Ensure config is loaded from {CONFIG_FILE}
6. Replace direct database operations with utilities from {DB_UTILS_PATH}, specifically:
   - Use connection.py for database connections, especially for MotherDuck integration
   - Import from dewey.core.db.connection for DatabaseConnection, get_motherduck_connection, get_connection
   - Use utils.py for schema operations and query building
7. Replace direct LLM calls with utilities from {LLM_UTILS_PATH}
8. Add Google-style docstrings with Args/Returns/Raises
9. Add type hints for all function signatures

Please use the full context of the file provided. Make sure the refactored code maintains all the
existing functionality.

# Project Conventions
{conventions_content}

# Base Script Implementation
{base_script_content}

# Configuration
{config_content}
"""

def build_test_prompt(source_file_path: Path, source_content: str, conventions_content: str, config_content: str, base_script_content: str) -> str:
    """Build the test generation prompt with all context.
    
    Args:
        source_file_path: Path to the source file being tested
        source_content: Content of the source file
        conventions_content: The content of the conventions.md file
        config_content: The content of the dewey.yaml file
        base_script_content: The content of the base_script.py file
        
    Returns:
        The complete test generation prompt with context
    """
    # Make sure the source_file_path is absolute
    source_file_path = source_file_path.resolve()
    
    # Get the module path relative to the src directory
    try:
        rel_path = source_file_path.relative_to(SRC_DIR)
        import_path = str(rel_path).replace('/', '.').replace('.py', '')
        if not import_path.startswith('dewey'):
            import_path = f"dewey.{import_path}"
    except ValueError:
        # If the file is not in the src directory, just use the file name
        import_path = source_file_path.stem
    
    return f"""
Generate comprehensive unit tests for the provided module.

Module path: {source_file_path}
Import path: {import_path}

The tests should follow these guidelines:
1. Use pytest fixtures wherever appropriate
2. Include tests for all public functions and methods
3. Cover edge cases and error conditions
4. Use mocking for external dependencies
5. Follow the Google Python style guide for docstrings
6. Include proper type hints
7. Add appropriate assertions to verify behavior
8. Use parametrized tests where appropriate for multiple test cases
9. Include proper setup and teardown methods if needed
10. Ensure high test coverage of the module's functionality

Please create a well-structured test file that thoroughly tests all aspects of the module.
The tests should be complete and ready to run.

# Source Module
```python
{source_content}
```

# Project Conventions
{conventions_content}

# Base Script Implementation
{base_script_content}

# Configuration
{config_content}
"""

def process_files_for_refactoring(
    source_files: list[Path], 
    model_name: str, 
    conventions_content: str,
    config_content: str,
    base_script_content: str,
    dry_run: bool = False
) -> None:
    """Process Python files for refactoring.
    
    Args:
        source_files: List of paths to Python files to refactor
        model_name: Name of the model to use
        conventions_content: Content of the conventions.md file
        config_content: Content of the config file
        base_script_content: Content of the base_script.py file
        dry_run: If True, don't actually modify the files
    """
    refactor_prompt = build_refactor_prompt(conventions_content, config_content, base_script_content)
    
    for file_path in source_files:
        try:
            logger.info(f"Refactoring {file_path}")
            if dry_run:
                continue

            # Use a null file for input history to avoid command issues
            null_history = os.devnull if os.name != 'nt' else 'NUL'
            io = InputOutput(yes=False, input_history_file=null_history)
            
            # Initialize model
            model = Model(model_name)
            
            # Create coder with the file
            coder = Coder.create(
                main_model=model,
                fnames=[str(file_path)],
                io=io
            )
            
            # Run refactoring
            coder.run(refactor_prompt)
            
        except Exception as e:
            logger.error(f"Failed to refactor {file_path}: {e}")

def generate_tests_for_files(
    source_files: list[Path],
    test_dir: Path,
    model_name: str,
    conventions_content: str,
    config_content: str,
    base_script_content: str,
    dry_run: bool = False
) -> None:
    """Generate tests for each source file.
    
    Args:
        source_files: List of paths to source Python files
        test_dir: Directory where tests should be stored
        model_name: Name of the model to use
        conventions_content: Content of the conventions.md file
        config_content: Content of the config file
        base_script_content: Content of the base_script.py file
        dry_run: If True, don't actually generate tests
    """
    for source_file in source_files:
        try:
            # Make sure the source file is absolute
            source_file = source_file.resolve()
            
            # Read the source file
            source_content = read_file(source_file)
            
            # Determine the test file path
            # First, try to get the relative path from SRC_DIR
            try:
                rel_path = source_file.relative_to(SRC_DIR)
                module_dir = rel_path.parent
            except ValueError:
                # If not in SRC_DIR, just use the file name
                module_dir = Path("")
                rel_path = Path(source_file.name)
            
            test_file_name = f"test_{source_file.name}"
            
            # Maintain the same directory structure in the test directory
            test_file_path = test_dir / "unit" / module_dir / test_file_name
            
            logger.info(f"Generating tests for {source_file} -> {test_file_path}")
            if dry_run:
                continue
            
            # Ensure the test directory exists
            test_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Use a null file for input history to avoid command issues
            null_history = os.devnull if os.name != 'nt' else 'NUL'
            io = InputOutput(yes=False, input_history_file=null_history)
            
            # Initialize model
            model = Model(model_name)
            
            # Create test file if it doesn't exist
            if not test_file_path.exists():
                with open(test_file_path, 'w') as f:
                    f.write("# Unit tests will be generated here\n")
                
            # Create coder with the test file
            coder = Coder.create(
                main_model=model,
                fnames=[str(test_file_path)],
                io=io
            )
            
            # Build test prompt
            test_prompt = build_test_prompt(
                source_file, 
                source_content, 
                conventions_content, 
                config_content, 
                base_script_content
            )
            
            # Run test generation
            coder.run(test_prompt)
            
        except Exception as e:
            logger.error(f"Failed to generate tests for {source_file}: {e}")

def main():
    """Function main."""
    parser = argparse.ArgumentParser(description="Refactor Python files and generate tests")
    parser.add_argument('--dry-run', action='store_true', help="Don't actually modify files")
    parser.add_argument('--src-dir', type=str, required=True, help="Directory or file containing source files to refactor")
    parser.add_argument('--test-dir', type=str, help="Directory for test files (defaults to PROJECT_ROOT/tests)")
    parser.add_argument('--model', type=str, default=DEFAULT_MODEL, help="Model to use for refactoring")
    parser.add_argument('--skip-refactor', action='store_true', help="Skip the refactoring phase")
    parser.add_argument('--skip-tests', action='store_true', help="Skip the test generation phase")
    parser.add_argument('--conventions-file', type=str, help="Path to conventions file (if different from default)")
    args = parser.parse_args()
    
    # Get source path - could be a file or directory
    source_path = Path(args.src_dir)
    if not source_path.exists():
        logger.error(f"Source path {source_path} does not exist")
        sys.exit(1)
    
    # Get test directory (default to PROJECT_ROOT/tests)
    test_dir = Path(args.test_dir) if args.test_dir else PROJECT_ROOT / "tests"
    if not test_dir.exists():
        logger.info(f"Creating test directory {test_dir}")
        test_dir.mkdir(parents=True, exist_ok=True)
    
    # Find Python files
    source_files = find_python_files(source_path)
    logger.info(f"Found {len(source_files)} Python files to process")
    
    # Use alternate conventions file if specified
    if args.conventions_file:
        global CONVENTIONS_FILE
        CONVENTIONS_FILE = Path(args.conventions_file)
    
    # Read context files
    conventions_content = read_conventions()
    config_content = read_config()
    base_script_content = read_base_script()
    
    # Phase 1: Refactor source files if not skipped
    if not args.skip_refactor:
        logger.info("Starting refactoring phase")
        process_files_for_refactoring(
            source_files, 
            args.model, 
            conventions_content,
            config_content,
            base_script_content,
            args.dry_run
        )
        logger.info("Refactoring phase complete")
    else:
        logger.info("Skipping refactoring phase")
    
    # Phase 2: Generate tests if not skipped
    if not args.skip_tests:
        logger.info("Starting test generation phase")
        generate_tests_for_files(
            source_files, 
            test_dir, 
            args.model, 
            conventions_content,
            config_content,
            base_script_content,
            args.dry_run
        )
        logger.info("Test generation phase complete")
    else:
        logger.info("Skipping test generation phase")
    
    logger.info("Processing complete")

if __name__ == "__main__":
    main() 