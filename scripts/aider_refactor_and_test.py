#!/usr/bin/env python3
"""
    Enhanced script for refactoring code and generating tests using Aider.

    This script provides a comprehensive workflow to:
    1. Refactor a given directory of Python files to match Dewey conventions
    2. Generate comprehensive unit tests for the refactored files
"""

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

from aider.coders import Coder
from aider.io import InputOutput
from aider.models import Model

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
    """
    Read a file and return its contents.

    Args:
    -----
        file_path: Path to the file to read

    Returns:
    --------
        The content of the file or empty string if file doesn't exist

"""
    try:
        with open(file_path) as f:
            return f.read()
    except Exception as e:
        logger.warning(f"Could not read file {file_path}: {str(e)}")
        return ""


def read_conventions() -> str:
    """
    Read the conventions.md file for context.

    Returns:
    --------
        The content of the conventions.md file

"""
    return read_file(CONVENTIONS_FILE)


def read_config() -> str:
"""
    Read the dewey.yaml config file for context.

    Returns:
    --------
        The content of the config file

"""
    return read_file(CONFIG_FILE)


def read_base_script() -> str:
"""
    Read the base_script.py file for context.

    Returns:
    --------
        The content of the base_script.py file

"""
    return read_file(BASE_SCRIPT_FILE)


def find_python_files(path: Path) -> list[Path]:
"""
    Find all Python files in the directory or return the given file if it's a Python file.

    Args:
    -----
        path: Path to a directory or a Python file

    Returns:
    --------
        List of paths to Python files

"""
    if path.is_file() and path.suffix == ".py":
        return [path]
    elif path.is_dir():
        return list(path.glob("**/*.py"))
    return []


def find_test_files(path: Path) -> list[Path]:
"""
    Find all test files in the directory.

    Args:
    -----
        path: Path to a directory

    Returns:
    --------
        List of paths to test files

"""
    if path.is_dir():
        return list(path.glob("**/test_*.py"))
    return []


def build_refactor_prompt(
    conventions_content: str, config_content: str, base_script_content: str
) -> str:
"""
    Build the refactor prompt with all context.

    Args:
    -----
        conventions_content: The content of the conventions.md file
        config_content: The content of the dewey.yaml file
        base_script_content: The content of the base_script.py file

    Returns:
    --------
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


def build_test_prompt(
    source_file_path: Path,
    source_content: str,
    conventions_content: str,
    config_content: str,
    base_script_content: str,
) -> str:
"""
    Build the test generation prompt with all context.

    Args:
    -----
        source_file_path: Path to the source file being tested
        source_content: Content of the source file
        conventions_content: The content of the conventions.md file
        config_content: The content of the dewey.yaml file
        base_script_content: The content of the base_script.py file

    Returns:
    --------
        The complete test generation prompt with context

"""
    # Make sure the source_file_path is absolute
    source_file_path = source_file_path.resolve()

    # Get the module path relative to the src directory
    try:
        rel_path = source_file_path.relative_to(SRC_DIR)
        import_path = str(rel_path).replace("/", ".").replace(".py", "")
        if not import_path.startswith("dewey"):
            import_path = f"dewey.{import_path}"
    except ValueError:
        # If the file is not in the src directory, just use the file name
        import_path = source_file_path.stem

    # Get corresponding test path
    parent_dir = source_file_path.parent
    module_name = source_file_path.stem

    return f"""
Generate comprehensive unit tests for the provided module that are compatible with the Dewey project structure.

Module path: {source_file_path}
Import path: {import_path}

The tests MUST follow these specific Dewey conventions:
1. Create a proper conftest.py file in the test directory if needed with appropriate test fixtures
2. Use pytest.fixture for all test dependencies, especially database connections, file system accesses, and external APIs
3. Mock ALL external dependencies including:
   - Database connections (use unittest.mock to patch dewey.core.db.connection functions)
   - File system operations (patch Path, open, etc.)
   - HTTP requests and API calls (patch requests, httpx, or other HTTP libraries)
   - LLM calls (patch OpenAI clients or similar)
4. Include proper type annotations for all test functions and fixtures
5. Create tests for ALL public methods and functions, including edge cases
6. Use parameterized tests with pytest.mark.parametrize for different input scenarios
7. Ensure tests can run in isolation without requiring any external dependencies
8. Include asserts for all expected behaviors, including error cases
9. If the code follows the BaseScript pattern, mock the BaseScript initialization
10. ALWAYS mock file system operations instead of actually reading/writing files

MOST IMPORTANT: The test file must be completely self-contained and runnable without ANY external dependencies or configurations.

Test structure requirements:
1. Import all necessary modules at the top, including typing imports (Dict, List, Any, Optional)
2. Define test fixtures in a pytest.fixture decorated function BEFORE tests that use them
3. Group tests by method or functionality
4. Add proper docstrings to test functions following Google style
5. Create proper assertions that test both function behavior and return values
6. Focus on edge cases and error conditions
7. Implement proper teardown to cleanup any resources

Here's an example format to follow:
```python
\"\"\"Tests for module_name.\"\"\"

import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional

from dewey.core.base_script import BaseScript
from {import_path} import *

@pytest.fixture
def mock_db_connection():
    \"\"\"Create a mock database connection.\"\"\"
    mock_conn = MagicMock()
    mock_conn.execute.return_value = pd.DataFrame({{"col1": [1, 2, 3]}})
    return mock_conn

@pytest.fixture
def mock_config() -> Dict[str, Any]:
    \"\"\"Create a mock configuration.\"\"\"
    return {{
        "settings": {{"key": "value"}},
        "database": {{"connection_string": "mock_connection"}}
    }}

# ... more fixtures as needed ...

@patch("dewey.core.db.connection.get_motherduck_connection")
def test_module_function(mock_get_conn, mock_db_connection, mock_config):
    \"\"\"Test that module_function works correctly.\"\"\"
    # Arrange
    mock_get_conn.return_value = mock_db_connection

    # Act
    result = module_function(param1, param2)

    # Assert
    assert result == expected_result
    mock_db_connection.execute.assert_called_once()
```

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
    dry_run: bool = False,
) -> None:
"""
    Process Python files for refactoring.

    Args:
    -----
        source_files: List of paths to Python files to refactor
        model_name: Name of the model to use
        conventions_content: Content of the conventions.md file
        config_content: Content of the config file
        base_script_content: Content of the base_script.py file
        dry_run: If True, don't actually modify the files

"""
    refactor_prompt = build_refactor_prompt(
        conventions_content, config_content, base_script_content
    )

    for file_path in source_files:
        try:
            logger.info(f"Refactoring {file_path}")
            if dry_run:
                continue

            # Use a null file for input history to avoid command issues
            null_history = os.devnull if os.name != "nt" else "NUL"
            io = InputOutput(yes=False, input_history_file=null_history)

            # Initialize model
            model = Model(model_name)

            # Create coder with the file
            coder = Coder.create(main_model=model, fnames=[str(file_path)], io=io)

            # Run refactoring
            coder.run(refactor_prompt)

        except Exception as e:
            logger.error(f"Failed to refactor {file_path}: {e}")


def run_generated_tests(
    test_dir: Path, source_files: list[Path], verbose: bool = False
) -> bool:
"""
    Run the generated tests using pytest.

    Args:
    -----
        test_dir: Directory containing test files
        source_files: List of source files that were tested
        verbose: Whether to show verbose output

    Returns:
    --------
        True if all tests passed, False otherwise

"""
    logger.info("Running generated tests...")

    # Create list of test files based on source files
    test_files = []
    for source_file in source_files:
        try:
            rel_path = source_file.relative_to(SRC_DIR)
            module_dir = rel_path.parent
        except ValueError:
            module_dir = Path("")
            rel_path = Path(source_file.name)

        test_file_name = f"test_{source_file.name}"
        test_file_path = test_dir / "unit" / module_dir / test_file_name

        if test_file_path.exists():
            test_files.append(str(test_file_path))

    if not test_files:
        logger.warning("No test files found to run")
        return False

    # Build pytest command
    cmd = ["pytest"]

    # Add test files
    cmd.extend(test_files)

    # Add verbose flag if requested
    if verbose:
        cmd.append("-v")

    # Run the tests
    logger.info(f"Running tests with command: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)

        # Log the output
        if result.stdout:
            for line in result.stdout.splitlines():
                logger.info(f"Test output: {line}")

        if result.stderr:
            for line in result.stderr.splitlines():
                logger.error(f"Test error: {line}")

        # Return True if tests passed
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        return False


def generate_tests_for_files(
    source_files: list[Path],
    test_dir: Path,
    model_name: str,
    conventions_content: str,
    config_content: str,
    base_script_content: str,
    dry_run: bool = False,
    make_testable: bool = True,  # New parameter to allow modifying source files
) -> None:
"""
    Generate tests for each source file.

    Args:
    -----
        source_files: List of paths to source Python files
        test_dir: Directory where tests should be stored
        model_name: Name of the model to use
        conventions_content: Content of the conventions.md file
        config_content: Content of the config file
        base_script_content: Content of the base_script.py file
        dry_run: If True, don't actually generate tests
        make_testable: If True, modify source files to make them more testable

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

            # Check if conftest.py exists in the test directory, create it if not
            conftest_path = test_file_path.parent / "conftest.py"
            if not conftest_path.exists():
                logger.info(f"Creating conftest.py at {conftest_path}")
                with open(conftest_path, "w") as f:
                    f.write("""\"\"\"Common test fixtures for this test directory.\"\"\"

import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from typing import Dict, Any

@pytest.fixture
def mock_db_connection():
    \"\"\"Create a mock database connection.\"\"\"
    mock_conn = MagicMock()
    mock_conn.execute.return_value = pd.DataFrame({"col1": [1, 2, 3]})
    return mock_conn

@pytest.fixture
def mock_config() -> Dict[str, Any]:
    \"\"\"Create a mock configuration.\"\"\"
    return {
        "settings": {"key": "value"},
        "database": {"connection_string": "mock_connection"}
    }
""")

            # Use a null file for input history to avoid command issues
            null_history = os.devnull if os.name != "nt" else "NUL"
            io = InputOutput(yes=False, input_history_file=null_history)

            # Initialize model
            model = Model(model_name)

            # Create test file if it doesn't exist
            if not test_file_path.exists():
                with open(test_file_path, "w") as f:
                    f.write(f"""\"\"\"Tests for {source_file.stem}.\"\"\"

import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, List, Any, Optional

# Import the module being tested
""")

            # First create/update the test file
            test_coder = Coder.create(
                main_model=model, fnames=[str(test_file_path)], io=io
            )

            # Build test prompt
            test_prompt = build_test_prompt(
                source_file,
                source_content,
                conventions_content,
                config_content,
                base_script_content,
            )

            # Run test generation
            test_coder.run(test_prompt)

            # If make_testable is True, also modify the source file to make it more testable
            if make_testable:
                # First, check if the generated test has issues that would require source changes
                generated_test_content = read_file(test_file_path)

                # Create a prompt to improve testability
                testability_prompt = f"""
Analyze the generated test file and the source file. Identify changes needed in the source file to make it more testable.
Focus on:
1. Dependency injection to replace hard-coded dependencies
2. Separating side effects from pure functions
3. Adding interfaces that can be mocked
4. Making private methods more accessible for testing if needed
5. Adding type hints for better test stubbing

Only suggest changes if they are necessary for better testing.

Test file:
```python
{generated_test_content}
```

Source file:
```python
{source_content}
```
"""

                # Create coder with the source file
                source_coder = Coder.create(
                    main_model=model, fnames=[str(source_file)], io=io
                )

                # Run source file improvement
                source_coder.run(testability_prompt)

                # After modifying the source, we might need to update the tests again
                # to reflect the changes in the source file

                # Re-read the modified source file
                modified_source_content = read_file(source_file)

                if modified_source_content != source_content:
                    logger.info("Source file was modified, updating tests to match...")

                    # Build a new test prompt with updated source
                    updated_test_prompt = build_test_prompt(
                        source_file,
                        modified_source_content,
                        conventions_content,
                        config_content,
                        base_script_content,
                    )

                    # Run test generation again
                    test_coder.run(updated_test_prompt)

        except Exception as e:
            logger.error(f"Failed to generate tests for {source_file}: {str(e)}")


def main():
    """Function main."""
    parser = argparse.ArgumentParser(
        description="Refactor Python files and generate tests"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Don't actually modify files"
    )
    parser.add_argument(
        "--src-dir",
        type=str,
        required=True,
        help="Directory or file containing source files to refactor",
    )
    parser.add_argument(
        "--test-dir",
        type=str,
        help="Directory for test files (defaults to PROJECT_ROOT/tests)",
    )
    parser.add_argument(
        "--model", type=str, default=DEFAULT_MODEL, help="Model to use for refactoring"
    )
    parser.add_argument(
        "--skip-refactor", action="store_true", help="Skip the refactoring phase"
    )
    parser.add_argument(
        "--skip-tests", action="store_true", help="Skip the test generation phase"
    )
    parser.add_argument(
        "--conventions-file",
        type=str,
        help="Path to conventions file (if different from default)",
    )
    parser.add_argument(
        "--no-testability",
        action="store_true",
        help="Don't modify source files for testability",
    )
    parser.add_argument(
        "--run-tests", action="store_true", help="Run tests after generating them"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)

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
            args.dry_run,
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
            args.dry_run,
            not args.no_testability,  # Use testability improvements unless --no-testability is set
        )
        logger.info("Test generation phase complete")
    else:
        logger.info("Skipping test generation phase")

    # Phase 3: Run generated tests if requested
    if args.run_tests and not args.skip_tests and not args.dry_run:
        logger.info("Starting test execution phase")
        success = run_generated_tests(test_dir, source_files, args.verbose)
        if success:
            logger.info("All tests passed successfully")
        else:
            logger.warning("Some tests failed")
        logger.info("Test execution phase complete")

    logger.info("Processing complete")


if __name__ == "__main__":
    main()
