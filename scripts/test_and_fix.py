#!/usr/bin/env python3
"""
Test and Fix Script - Runs tests and uses Aider to fix failing tests
"""

import argparse
import logging
import os
import subprocess
import sys
import re
import tempfile
import json
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Set, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("test_and_fix")

# Import local aider_refactor script
try:
    from aider_refactor import fix_file_with_aider
except ImportError:
    logger.error("Error: Unable to import aider_refactor module. Make sure it's in the same directory.")
    sys.exit(1)

# Try to import repomix if available
try:
    import repomix
    HAS_REPOMIX = True
except ImportError:
    logger.info("Repomix not available; repository context will be limited. Consider installing with 'pip install repomix'")
    HAS_REPOMIX = False


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run tests and fix failing code using Aider."
    )
    parser.add_argument(
        "--dir",
        required=True,
        help="Directory or file to process",
    )
    parser.add_argument(
        "--test-dir",
        default="tests",
        help="Directory containing tests (default: tests)",
    )
    parser.add_argument(
        "--model",
        default="deepinfra/google/gemini-2.0-flash-001",
        help="Model to use (default: deepinfra/google/gemini-2.0-flash-001)",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=5,
        help="Maximum number of iterations to run (default: 5)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't make any changes, just show what would be done",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Timeout in seconds for processing each file (default: 120)",
    )
    parser.add_argument(
        "--conventions-file",
        default="CONVENTIONS.md",
        help="Path to conventions file (default: CONVENTIONS.md)",
    )
    parser.add_argument(
        "--persist-session",
        action="store_true",
        help="Use a persistent Aider session to maintain context across files",
    )
    parser.add_argument(
        "--session-dir",
        default=".aider",
        help="Directory to store persistent session files (default: .aider)",
    )
    parser.add_argument(
        "--skip-refactor",
        action="store_true",
        help="Skip refactoring step and only run tests",
    )
    parser.add_argument(
        "--no-testability",
        action="store_true",
        help="Don't modify source files for testability",
    )
    return parser.parse_args()


def normalize_path(path: str) -> str:
    """Convert directory path to test module format."""
    # Remove "src/" prefix if present
    if path.startswith("src/"):
        path = path[4:]
    
    # Convert slashes to dots
    path = path.replace("/", ".")
    
    return path


def run_tests(directory: str, test_dir: str, verbose: bool = False, timeout: int = 60) -> Tuple[bool, List[str], Dict[str, List[str]]]:
    """
    Run pytest for the specified directory.
    
    Args:
        directory: Directory path to run tests for
        test_dir: Directory containing tests
        verbose: Enable verbose output
        timeout: Maximum time in seconds to wait for tests to complete
    
    Returns:
        Tuple containing:
        - Boolean indicating if tests passed
        - List of error messages
        - Dict mapping source files to error messages
    """
    # Normalize directory for test discovery
    module_path = normalize_path(directory)
    
    # Determine test path based on the module structure
    test_path = f"{test_dir}/unit/{module_path}"
    if not os.path.exists(test_path):
        # Try with different test path formats
        alternate_path = f"{test_dir}/unit/{module_path.replace('.', '/')}"
        if os.path.exists(alternate_path):
            test_path = alternate_path
        else:
            logger.warning(f"Test directory {test_path} not found, running all tests for {module_path}")
            test_path = f"{test_dir}"
    
    # Build pytest command
    cmd = ["python", "-m", "pytest", test_path, "-v"]
    if verbose:
        logger.info(f"Running command: {' '.join(cmd)}")
    
    # Run the tests with timeout
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        logger.error(f"Test execution timed out after {timeout} seconds")
        return False, ["Test execution timed out"], {directory: ["Test execution timed out"]}
    
    # Parse output for errors
    output_lines = result.stdout.splitlines() + result.stderr.splitlines()
    
    # Log the first few lines of output for debugging if verbose
    if verbose and output_lines:
        logger.info("First few lines of test output:")
        for line in output_lines[:min(10, len(output_lines))]:
            logger.info(f"  {line}")
        if len(output_lines) > 10:
            logger.info(f"  ... and {len(output_lines) - 10} more lines")
    
    # Check for syntax errors in any Python files
    error_patterns = [
        (r'ImportError while loading conftest \'([^\']+)\'', "ImportError in conftest"),
        (r'SyntaxError: (.*) \(([^,]+),', "SyntaxError"),
        (r'IndentationError: (.*) \(([^,]+),', "IndentationError"),
        (r'File "([^"]+)", line \d+\s*\n\s*(?:[^\n]+\n\s*)*?\s*(\w+Error:.*)', "Generic Error"),
        (r'E\s+File "([^"]+)", line \d+.*\n\s+(\w+Error:.*)', "Pytest Error"),
        (r'ImportError: cannot import name \'([^\']+)\' from \'([^\']+)\'', "Import Name Error"),
        (r'AttributeError: \'?([^\']+)\'? has no attribute \'([^\']+)\'', "Attribute Error"),
        (r'TypeError: (.*)', "Type Error"),
        (r'ValueError: (.*)', "Value Error"),
        (r'FAILED ([^ ]+) - (.+)', "Test Failure"),
    ]
    
    for i, line in enumerate(output_lines):
        for pattern, error_type in error_patterns:
            match = re.search(pattern, line)
            if match:
                if error_type == "ImportError in conftest":
                    error_file = match.group(1)
                    # Look for associated error message in nearby lines
                    error_msg = "Syntax error in conftest"
                    for j in range(i, min(i + 20, len(output_lines))):
                        if any(err in output_lines[j] for err in ["SyntaxError", "IndentationError", "ImportError"]):
                            error_msg = output_lines[j].strip()
                            break
                elif error_type in ("SyntaxError", "IndentationError"):
                    error_msg = match.group(1).strip()
                    error_file = match.group(2).strip()
                elif error_type == "Import Name Error":
                    name = match.group(1)
                    module = match.group(2)
                    error_msg = f"Cannot import name '{name}' from '{module}'"
                    # Try to determine the source file
                    error_file = module.replace('.', '/') + '.py'
                    if not os.path.exists(error_file) and error_file.startswith('src/'):
                        error_file = error_file[4:]  # Try without 'src/' prefix
                elif error_type == "Attribute Error":
                    obj = match.group(1)
                    attr = match.group(2)
                    error_msg = f"'{obj}' has no attribute '{attr}'"
                    # Try to find the file this is happening in by looking at context
                    error_file = directory
                    for j in range(max(0, i-5), min(i+5, len(output_lines))):
                        file_match = re.search(r'File "([^"]+)"', output_lines[j])
                        if file_match and '/site-packages/' not in file_match.group(1):
                            error_file = file_match.group(1)
                            break
                elif error_type == "Test Failure":
                    test_path = match.group(1)
                    error_msg = match.group(2)
                    # Try to derive the source file from the test path
                    if "test_" in test_path:
                        source_name = test_path.split("test_")[-1].split("::")[0].replace(".py", ".py")
                        error_file = os.path.join(directory, source_name)
                        if not os.path.exists(error_file):
                            # If we can't find the source file, use the directory
                            error_file = directory
                    else:
                        error_file = directory
                else:
                    error_file = match.group(1)
                    error_msg = match.group(2).strip() if len(match.groups()) > 1 else line.strip()
                
                # Make sure it's a source file not a library
                if '/site-packages/' not in error_file and (error_file.startswith('src/') or 'tests/' in error_file or 'conftest.py' in error_file):
                    logger.warning(f"{error_type} detected in {error_file}: {error_msg}")
                    return False, [f"{error_type} in {error_file}: {error_msg}"], {error_file: [error_msg]}
    
    # Look for assertion errors in test output
    assertion_pattern = re.compile(r'(?:E\s+|>)\s*assert\s+(.*)')
    for i, line in enumerate(output_lines):
        match = assertion_pattern.search(line)
        if match:
            # Look backward for the test file
            test_file = None
            for j in range(i, max(0, i-20), -1):
                file_match = re.search(r'(?:FAILED|ERROR)\s+([^\s]+)::', output_lines[j])
                if file_match:
                    test_file = file_match.group(1)
                    break
            
            if test_file:
                # Try to determine source file from test file
                if test_file.startswith('tests/unit/'):
                    # Extract module path from test file
                    module_path = test_file.replace('tests/unit/', '').replace('.py', '')
                    if module_path.startswith('dewey/'):
                        module_path = module_path[6:]  # Remove 'dewey/' prefix
                    
                    # Map to source file
                    source_file = f"src/dewey/{module_path.replace('test_', '')}.py"
                    if not os.path.exists(source_file):
                        # Try without test_ prefix
                        source_file = directory
                    
                    error_msg = f"Assertion failed: {match.group(1)}"
                    logger.warning(f"Assertion failure in test {test_file} affecting {source_file}: {error_msg}")
                    return False, [f"Assertion failure in {test_file}: {error_msg}"], {source_file: [error_msg]}
    
    # Check for common patterns that indicate no tests ran
    no_tests_patterns = [
        "no tests ran",
        "no tests collected",
        "collected 0 items",
        "deselected all"
    ]
    
    for line in output_lines:
        lower_line = line.lower()
        if any(pattern in lower_line for pattern in no_tests_patterns):
            if verbose:
                logger.info("No tests were found for this directory")
            return True, [], {}  # Treat as success if no tests
    
    # Get summary of test results
    test_summary = ""
    for line in output_lines:
        if "=" in line and any(x in line for x in ["passed", "failed", "error", "skipped"]):
            test_summary = line.strip()
            break
    
    if test_summary and "failed=0" in test_summary and "error=0" in test_summary:
        # All tests passed based on the summary
        if verbose:
            logger.info(f"All tests passed! {test_summary}")
        return True, [], {}
    
    # Determine if tests passed based on return code
    tests_passed = result.returncode == 0
    if tests_passed:
        if verbose:
            if test_summary:
                logger.info(f"All tests passed! {test_summary}")
            else:
                logger.info("All tests passed!")
        return True, [], {}
    
    # Tests failed, so parse error messages and map them to source files
    errors = []
    file_errors: Dict[str, List[str]] = {}
    
    # Regular expressions to identify error locations
    error_file_pattern = re.compile(r'(E\s+)?(src/\S+\.py):(\d+)(?::(\d+))?: (.*)')
    traceback_pattern = re.compile(r'\s*File "([^"]+)", line (\d+), in (.*)')
    
    # FAILED test_module.py::test_function - AssertionError
    failed_test_pattern = re.compile(r'FAILED\s+([^:]+)::([^\s]+)(\s+-\s+(.*))?')
    
    current_error = ""
    current_file = None
    
    for line in output_lines:
        # Look for failed test patterns
        failed_match = failed_test_pattern.search(line)
        if failed_match:
            test_file = failed_match.group(1)
            test_func = failed_match.group(2)
            error_in_line = failed_match.group(4) if failed_match.group(3) else "Test failed"
            
            current_error = f"Test {test_func} failed: {error_in_line}"
            
            # Try to derive source file from test file
            source_file = None
            if test_file.startswith('tests/unit/'):
                path_parts = test_file.replace('tests/unit/', '').replace('.py', '').split('/')
                if len(path_parts) > 1 and path_parts[0] == 'dewey':
                    # Remove 'dewey' prefix
                    path_parts = path_parts[1:]
                
                if test_func.startswith('test_'):
                    # Remove test_ prefix from the function name to try to identify the function being tested
                    function_name = test_func[5:]
                    
                    # Try to find the source file
                    for root_dir in ['src/dewey', 'src']:
                        # First, try with the full path
                        src_path = f"{root_dir}/{'/'.join(path_parts)}.py"
                        if os.path.exists(src_path):
                            source_file = src_path
                            break
                        
                        # Next, try with parent directory
                        if len(path_parts) > 1:
                            src_path = f"{root_dir}/{'/'.join(path_parts[:-1])}.py"
                            if os.path.exists(src_path):
                                source_file = src_path
                                break
            
            # If we couldn't derive the source file, use the directory
            if not source_file:
                source_file = directory
            
            if source_file not in file_errors:
                file_errors[source_file] = []
            file_errors[source_file].append(current_error)
            errors.append(current_error)
            
        # Look for error locations in source files
        file_match = error_file_pattern.search(line)
        if file_match:
            src_file = file_match.group(2)
            error_msg = file_match.group(5)
            errors.append(f"{src_file}: {error_msg}")
            
            if src_file not in file_errors:
                file_errors[src_file] = []
            file_errors[src_file].append(error_msg)
            current_file = src_file
            
        # Also check for traceback information
        tb_match = traceback_pattern.search(line)
        if tb_match:
            tb_file = tb_match.group(1)
            if tb_file.startswith('src/') and '/site-packages/' not in tb_file:
                # This is a source file, not a library
                if tb_file not in file_errors:
                    file_errors[tb_file] = []
                if current_error:
                    file_errors[tb_file].append(current_error)
                    current_error = ""
    
    # If we still couldn't find any specific source files, fallback to the target directory
    if not file_errors:
        file_errors[directory] = ["Failed tests detected but couldn't identify specific source files"]
        for error in errors:
            file_errors[directory].append(error)
        
        if not errors:
            # Just add the test summary if we have it
            if test_summary:
                file_errors[directory].append(f"Test summary: {test_summary}")
            else:
                file_errors[directory].append("Tests failed with unknown errors")
    
    if verbose:
        if test_summary:
            logger.info(f"Tests failed: {test_summary}")
        else:
            logger.info(f"Tests failed with {len(errors)} errors")
            
        for error in errors[:5]:
            logger.info(f"  {error}")
        if len(errors) > 5:
            logger.info(f"  ... and {len(errors) - 5} more errors")
    
    return False, errors, file_errors


def generate_fix_prompt(file_path: str, error_messages: List[str], additional_context: Optional[str] = None) -> str:
    """
    Generate a prompt for Aider to fix a specific file based on test failures.
    
    Args:
        file_path: Path to the file that needs to be fixed
        error_messages: List of error messages related to this file
        additional_context: Additional context to include in the prompt
        
    Returns:
        Prompt for Aider
    """
    prompt = f"Fix the following test failures in {file_path}:\n\n"
    
    for i, error in enumerate(error_messages, 1):
        prompt += f"{i}. {error}\n"
    
    prompt += "\nPlease update the file to fix these issues while maintaining the existing functionality."
    
    if additional_context:
        prompt += f"\n\nAdditional context:\n{additional_context}"
    
    return prompt


def get_repo_context(directory: str, verbose: bool = False) -> Dict[str, Any]:
    """
    Generate a repository context using repomix if available, or a simpler approach if not.
    
    Args:
        directory: Directory to analyze
        verbose: Enable verbose output
        
    Returns:
        Dictionary with repository context information
    """
    repo_context = {}
    
    # Create a simple file list if repomix isn't available
    if not HAS_REPOMIX:
        if verbose:
            logger.info("Using fallback method to create repository context (repomix not available)")
        
        # Find Python files in the directory
        try:
            python_files = {}
            dir_path = Path(directory)
            if dir_path.is_dir():
                for py_file in dir_path.glob("**/*.py"):
                    rel_path = py_file.relative_to(Path.cwd())
                    try:
                        with open(py_file, 'r') as f:
                            content = f.read()
                        
                        # Extract imports
                        imports = []
                        import_lines = re.findall(r'^(?:from|import)\s+[^\n]+', content, re.MULTILINE)
                        for line in import_lines:
                            imports.append(line.strip())
                        
                        # Extract classes and functions (very basic)
                        classes = re.findall(r'class\s+(\w+)', content)
                        functions = re.findall(r'def\s+(\w+)', content)
                        
                        python_files[str(rel_path)] = {
                            "imports": imports,
                            "classes": classes,
                            "functions": functions,
                            "content": content[:500] + "..." if len(content) > 500 else content
                        }
                    except Exception as e:
                        logger.error(f"Error reading file {py_file}: {e}")
            
            repo_context["files"] = python_files
        except Exception as e:
            logger.error(f"Error creating repository context: {e}")
    else:
        try:
            if verbose:
                logger.info(f"Generating repository context for {directory} using repomix")
            
            # Use repomix to create a repository map
            # Get the repository structure
            repo_map = repomix.get_repo_map(directory)
            
            # Get summaries of each file
            file_summaries = []
            for file_path in repo_map.get("python_files", []):
                if os.path.exists(file_path):
                    try:
                        summary = repomix.summarize_file(file_path)
                        file_summaries.append({
                            "path": file_path,
                            "summary": summary
                        })
                    except Exception as e:
                        logger.error(f"Error summarizing file {file_path}: {e}")
            
            repo_context = {
                "repo_map": repo_map,
                "file_summaries": file_summaries
            }
            
            if verbose:
                logger.info(f"Generated context for {len(file_summaries)} files")
        except Exception as e:
            logger.error(f"Error generating repository context with repomix: {e}")
    
    return repo_context


def fix_failing_files(
    file_errors: Dict[str, List[str]],
    model_name: str,
    dry_run: bool = False,
    conventions_file: Optional[str] = None,
    verbose: bool = False,
    timeout: int = 120,
    persist_session: bool = False,
    session_dir: str = ".aider",
    no_testability: bool = False,
) -> List[str]:
    """Fix failing files using Aider.
    
    Args:
        file_errors: Dict mapping files to their error messages
        model_name: Model to use for fixing
        dry_run: Don't actually make changes, just simulate
        conventions_file: Path to project conventions file
        verbose: Enable verbose output
        timeout: Maximum time in seconds to spend on each file
        persist_session: Whether to use a persistent Aider session
        session_dir: Directory to store session files
        no_testability: Don't modify source files for testability
        
    Returns:
        List of modified files
    """
    modified_files = []
    
    for file_path, errors in file_errors.items():
        if not os.path.exists(file_path):
            logger.warning(f"File {file_path} does not exist, skipping")
            continue
            
        logger.info(f"Fixing file: {file_path}")
        
        # Skip fixing if dry run
        if dry_run:
            logger.info(f"[DRY RUN] Would fix {file_path} for the following errors:")
            for error in errors:
                logger.info(f" - {error}")
            continue
        
        # Get additional context for the fix
        repo_context = get_repo_context(file_path, verbose)
        
        # Generate prompt for fixing the file
        fix_prompt = generate_fix_prompt(file_path, errors, repo_context.get("summary", ""))
        
        try:
            # Determine if this is a test file or a source file
            is_test = "test_" in os.path.basename(file_path) or "tests/" in file_path
            
            if is_test:
                # If it's a test file, we need to find the corresponding source file
                source_file = None
                test_basename = os.path.basename(file_path)
                if test_basename.startswith("test_"):
                    source_basename = test_basename[5:]  # Remove "test_" prefix
                    source_dir = os.path.dirname(file_path).replace("tests/unit", "src")
                    potential_source = os.path.join(source_dir, source_basename)
                    if os.path.exists(potential_source):
                        source_file = potential_source
                
                # If we found a source file and testability is enabled, we'll modify both
                if source_file and not no_testability:
                    logger.info(f"Found corresponding source file: {source_file}")
                    # First, fix the test file
                    fix_file_with_aider(
                        file_path,
                        fix_prompt,
                        model_name,
                        verbose=verbose,
                        timeout=timeout,
                        persist_session=persist_session,
                        session_dir=session_dir
                    )
                    modified_files.append(file_path)
                    
                    # Now, make the source file more testable
                    make_testable_prompt = f"""
This test file has issues with the source file {source_file}. Please modify the source file to make it more testable.
Focus on:
1. Adding dependency injection
2. Extracting complex logic into testable functions
3. Adding appropriate interfaces
4. Improving error handling
5. Adding type hints

The goal is to make the source file compatible with the test that we're trying to write.

Here's the current state of the test file with issues:
```python
{open(file_path, 'r').read()}
```

And here's the source file that needs to be modified:
```python
{open(source_file, 'r').read()}
```

Please improve the source file to make it more testable while preserving its functionality.
"""
                    # Now fix the source file
                    fix_file_with_aider(
                        source_file,
                        make_testable_prompt,
                        model_name,
                        verbose=verbose,
                        timeout=timeout,
                        persist_session=persist_session,
                        session_dir=session_dir
                    )
                    modified_files.append(source_file)
                    
                    # Fix the test file again with the updated source
                    updated_test_prompt = f"""
The source file has been updated to be more testable. Please update the test file to match the new source file.

Here's the updated source file:
```python
{open(source_file, 'r').read()}
```

Here's the current test file that needs to be fixed:
```python
{open(file_path, 'r').read()}
```

Please update the test to work with the modified source file.
"""
                    fix_file_with_aider(
                        file_path,
                        updated_test_prompt,
                        model_name,
                        verbose=verbose,
                        timeout=timeout,
                        persist_session=persist_session,
                        session_dir=session_dir
                    )
                else:
                    # Just fix the test file normally
                    fix_file_with_aider(
                        file_path,
                        fix_prompt,
                        model_name,
                        verbose=verbose,
                        timeout=timeout,
                        persist_session=persist_session,
                        session_dir=session_dir
                    )
                    modified_files.append(file_path)
            else:
                # It's a source file, just fix it normally
                fix_file_with_aider(
                    file_path,
                    fix_prompt,
                    model_name,
                    verbose=verbose,
                    timeout=timeout,
                    persist_session=persist_session,
                    session_dir=session_dir
                )
                modified_files.append(file_path)
                
                # Additionally, generate or fix tests if testability is enabled
                if not no_testability:
                    # Figure out the test file path for this source file
                    source_basename = os.path.basename(file_path)
                    test_basename = f"test_{source_basename}"
                    source_rel_path = os.path.relpath(file_path)
                    
                    # Convert src/path/to/file.py to tests/unit/path/to/test_file.py
                    if source_rel_path.startswith("src/"):
                        source_rel_path = source_rel_path[4:]  # Remove "src/" prefix
                    test_path = os.path.join("tests/unit", os.path.dirname(source_rel_path), test_basename)
                    
                    # Check if the test file exists
                    if os.path.exists(test_path):
                        # Fix the existing test file
                        logger.info(f"Fixing existing test file: {test_path}")
                        fix_test_prompt = f"""
The source file has been updated. Please update the test file to work with the modified source.

Source file:
```python
{open(file_path, 'r').read()}
```

Current test file:
```python
{open(test_path, 'r').read()}
```

Please update the test to work correctly with the source file.
"""
                        fix_file_with_aider(
                            test_path,
                            fix_test_prompt,
                            model_name,
                            verbose=verbose,
                            timeout=timeout,
                            persist_session=persist_session,
                            session_dir=session_dir
                        )
                        modified_files.append(test_path)
                    else:
                        # Create the test directory if it doesn't exist
                        test_dir = os.path.dirname(test_path)
                        if not os.path.exists(test_dir):
                            os.makedirs(test_dir, exist_ok=True)
                        
                        # Create a new test file
                        logger.info(f"Creating new test file: {test_path}")
                        with open(test_path, 'w') as f:
                            f.write(f"""\"\"\"Tests for {os.path.basename(file_path)}.\"\"\"

import pytest
from unittest.mock import patch, MagicMock

# Import the module being tested
""")
                            
                        generate_test_prompt = f"""
Please create comprehensive unit tests for the source file. The tests should follow Dewey conventions:
1. Use pytest fixtures for all dependencies
2. Mock external dependencies (database, files, APIs)
3. Include tests for all public functions with edge cases
4. Use parameterized tests where appropriate
5. Ensure tests can run in isolation

Source file:
```python
{open(file_path, 'r').read()}
```

Please create tests that verify the functionality while following best practices.
"""
                        fix_file_with_aider(
                            test_path,
                            generate_test_prompt,
                            model_name,
                            verbose=verbose,
                            timeout=timeout,
                            persist_session=persist_session,
                            session_dir=session_dir
                        )
                        modified_files.append(test_path)
                        
                        # Check if we need to create a conftest.py file
                        conftest_path = os.path.join(os.path.dirname(test_path), "conftest.py")
                        if not os.path.exists(conftest_path):
                            logger.info(f"Creating conftest.py at {conftest_path}")
                            with open(conftest_path, 'w') as f:
                                f.write("""\"\"\"Common test fixtures for this directory.\"\"\"

import pytest
from unittest.mock import MagicMock, patch
import pandas as pd

@pytest.fixture
def mock_db_connection():
    \"\"\"Create a mock database connection.\"\"\"
    mock_conn = MagicMock()
    mock_conn.execute.return_value = pd.DataFrame({"col1": [1, 2, 3]})
    return mock_conn

@pytest.fixture
def mock_config():
    \"\"\"Create a mock configuration.\"\"\"
    return {
        "settings": {"key": "value"},
        "database": {"connection_string": "mock_connection"}
    }
""")
                            modified_files.append(conftest_path)
                
        except Exception as e:
            logger.error(f"Error fixing file {file_path}: {e}")
            continue
    
    return modified_files


def analyze_test_files(test_path: str, failed_tests: List[str]) -> Dict[str, str]:
    """
    Analyze test files to understand what's being tested and expected.
    
    Args:
        test_path: Path to the test directory
        failed_tests: List of failed test identifiers (e.g., 'test_function')
        
    Returns:
        Dict mapping test functions to their source code
    """
    test_contents = {}
    
    # Find all Python test files in the directory
    test_files = list(Path(test_path).glob("**/*.py"))
    
    for test_file in test_files:
        try:
            with open(test_file, 'r') as f:
                content = f.read()
                
            # Look for test functions that match the failed tests
            for failed_test in failed_tests:
                # Extract just the function name if it includes the module path
                test_name = failed_test.split('::')[-1] if '::' in failed_test else failed_test
                
                # Simple pattern to find the test function definition
                pattern = f"def {test_name}\\("
                if re.search(pattern, content):
                    # Extract the test function definition
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if re.search(pattern, line):
                            # Extract the function and its body
                            function_lines = [line]
                            j = i + 1
                            indent = len(line) - len(line.lstrip())
                            # Get the indented block
                            while j < len(lines) and (not lines[j].strip() or len(lines[j]) - len(lines[j].lstrip()) > indent):
                                function_lines.append(lines[j])
                                j += 1
                            test_contents[test_name] = '\n'.join(function_lines)
                            break
        except Exception as e:
            logger.error(f"Error analyzing test file {test_file}: {e}")
    
    return test_contents


def main():
    """Main function."""
    args = parse_args()
    
    # Enable verbose logging if requested
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG)
    
    directory = args.dir
    if not os.path.exists(directory):
        logger.error(f"Directory or file not found: {directory}")
        sys.exit(1)
    
    # Set up fixed paths
    directory = os.path.abspath(directory)
    test_dir = os.path.abspath(args.test_dir)
    
    logger.info(f"Processing: {directory}")
    logger.info(f"Test directory: {test_dir}")
    
    # If target is a file, extract directory for test discovery
    target_files = []
    if os.path.isfile(directory):
        target_files = [directory]
        directory = os.path.dirname(directory)
    
    iteration = 0
    all_modified_files = set()
    
    # Create session directory if using persistent sessions
    if args.persist_session:
        os.makedirs(args.session_dir, exist_ok=True)
    
    # Keep running the test-fix cycle until all tests pass or max iterations is reached
    while iteration < args.max_iterations:
        iteration += 1
        logger.info(f"\n===== Iteration {iteration}/{args.max_iterations} =====")
        
        # Run the tests
        try:
            passed, errors, file_errors = run_tests(directory, test_dir, args.verbose, args.timeout)
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            sys.exit(1)
        
        if passed:
            logger.info("All tests have passed!")
            break
        
        # If target_files were specified, filter file_errors to include only those files
        if target_files:
            file_errors = {f: errs for f, errs in file_errors.items() if f in target_files}
        
        # Fix failing files
        try:
            modified_files = fix_failing_files(
                file_errors,
                args.model,
                args.dry_run,
                args.conventions_file,
                args.verbose,
                args.timeout,
                args.persist_session,
                args.session_dir,
                args.no_testability
            )
            for file in modified_files:
                all_modified_files.add(file)
        except Exception as e:
            logger.error(f"Error fixing files: {e}")
            sys.exit(1)
        
        # If no files were modified, break out of the loop
        if not modified_files and not args.dry_run:
            logger.warning("No files were modified in this iteration, stopping")
            break
        
        # If doing a dry run, we'll just pretend it's fixed and exit
        if args.dry_run:
            logger.info("[DRY RUN] Simulating success after modifications")
            break
    
    if iteration >= args.max_iterations and not passed:
        logger.warning(f"Reached maximum iterations ({args.max_iterations}) without passing all tests")
        sys.exit(1)
    else:
        logger.info(f"Fixed {len(all_modified_files)} files: {', '.join(all_modified_files)}")
        sys.exit(0)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.warning("Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1) 