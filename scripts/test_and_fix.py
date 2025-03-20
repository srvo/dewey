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
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Set

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


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run tests and fix failures using Aider."
    )
    parser.add_argument(
        "--dir",
        type=str,
        required=True,
        help="Directory to process (e.g., src/dewey/core/db)",
    )
    parser.add_argument(
        "--test-dir",
        type=str,
        default="tests",
        help="Directory containing tests (default: tests)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="deepinfra/google/gemini-2.0-flash-001",
        help="Model to use for refactoring",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=5,
        help="Maximum number of test-fix iterations (default: 5)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't make any changes, just show what would be done",
    )
    parser.add_argument(
        "--conventions-file",
        type=str,
        default="CONVENTIONS.md",
        help="Path to conventions file",
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
        help="Timeout in seconds for processing each file with Aider",
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


def fix_failing_files(
    file_errors: Dict[str, List[str]],
    model_name: str,
    dry_run: bool = False,
    conventions_file: Optional[str] = None,
    verbose: bool = False,
    timeout: int = 120,
) -> List[str]:
    """
    Fix files with failing tests using Aider.
    
    Args:
        file_errors: Dict mapping source files to error messages
        model_name: AI model to use
        dry_run: If True, don't make actual changes
        conventions_file: Path to coding conventions file
        verbose: Enable verbose output
        timeout: Timeout in seconds for processing each file
        
    Returns:
        List of files that were fixed
    """
    fixed_files = []
    
    if not file_errors:
        logger.warning("No files with errors identified")
        return fixed_files
    
    # Sort files by number of errors (prioritize files with more errors)
    sorted_files = sorted(file_errors.items(), key=lambda x: len(x[1]), reverse=True)
    
    for file_path, errors in sorted_files:
        if verbose:
            logger.info(f"Attempting to fix {file_path} with {len(errors)} errors")
        
        # Create a Path object
        path = Path(file_path)
        if not path.exists():
            logger.warning(f"File {file_path} does not exist, skipping")
            continue
        
        # Generate prompt for Aider
        prompt = generate_fix_prompt(file_path, errors)
        
        # Set up environment for fix_file_with_aider
        if fix_file_with_aider(
            path,
            model_name,
            dry_run=dry_run,
            conventions_file=conventions_file,
            verbose=verbose,
            timeout=timeout,
            custom_prompt=prompt,
        ):
            fixed_files.append(file_path)
            if verbose:
                logger.info(f"Successfully applied fixes to {file_path}")
        else:
            logger.warning(f"Failed to fix {file_path}")
    
    return fixed_files


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
    """Main function to run the script."""
    args = parse_args()
    directory = args.dir
    
    if not os.path.exists(directory):
        logger.error(f"Error: Directory {directory} does not exist")
        sys.exit(1)
    
    logger.info(f"Starting test-and-fix process for {directory}")
    logger.info(f"Maximum iterations: {args.max_iterations}")
    
    # Check if there are any test files for this directory
    module_path = normalize_path(directory)
    test_paths = [
        f"{args.test_dir}/unit/{module_path}",
        f"{args.test_dir}/unit/{module_path.replace('.', '/')}",
        f"{args.test_dir}/integration/{module_path}",
        f"{args.test_dir}/integration/{module_path.replace('.', '/')}"
    ]
    
    has_test_files = False
    for test_path in test_paths:
        if os.path.exists(test_path):
            # Check if there are any .py files
            py_files = list(Path(test_path).glob("**/*.py"))
            if py_files:
                has_test_files = True
                break
    
    if not has_test_files:
        logger.warning(f"No test files found for {directory}")
        logger.info("No tests to run means no failures to fix. Exiting with success.")
        return 0
    
    # Track if any real fixes were attempted
    fixes_attempted = False
    
    iteration = 1
    while iteration <= args.max_iterations:
        logger.info(f"Iteration {iteration}/{args.max_iterations}")
        
        # Step 1: Run tests
        logger.info("Running tests...")
        tests_passed, errors, file_errors = run_tests(directory, args.test_dir, args.verbose, args.timeout)
        
        # If tests pass, we're done
        if tests_passed and not args.dry_run:
            logger.info(f"All tests passed after {iteration} iterations!")
            return 0
        elif tests_passed and args.dry_run:
            logger.info(f"All tests would pass after applying the suggested fixes!")
            return 0
        
        # Check if we need to fix a conftest.py file first
        conftest_files = [file for file in file_errors.keys() if "conftest.py" in file]
        if conftest_files:
            conftest_file = conftest_files[0]
            logger.warning(f"Detected issue in {conftest_file}. Fixing this file first...")
            
            conftest_path = Path(conftest_file)
            if not conftest_path.exists():
                logger.error(f"Conftest file {conftest_file} does not exist")
                return 1
            
            # Create a more specific prompt for the conftest file
            conftest_errors = file_errors[conftest_file]
            conftest_prompt = f"Fix the syntax error in {conftest_file}:\n\n"
            for error in conftest_errors:
                conftest_prompt += f"- {error}\n"
            conftest_prompt += "\nThis file needs to be fixed before any tests can run. Please correct the syntax issues."
            
            # Try to fix the conftest file - allow multiple attempts (up to 3)
            max_conftest_attempts = 3
            for attempt in range(1, max_conftest_attempts + 1):
                logger.info(f"Attempt {attempt}/{max_conftest_attempts} to fix {conftest_file}")
                
                # If this is a subsequent attempt, enhance the prompt
                if attempt > 1:
                    conftest_prompt += f"\n\nThis is attempt {attempt}. Previous attempts failed to completely fix the syntax error. Please be more thorough in your fix."
                
                fix_result = fix_file_with_aider(
                    conftest_path,
                    args.model,
                    args.dry_run,
                    args.conventions_file,
                    args.verbose,
                    args.timeout,
                    False,  # check_for_urls
                    conftest_prompt,
                )
                
                if fix_result:
                    logger.info(f"Successfully fixed {conftest_file}")
                    fixes_attempted = True
                    # Verify the fix by trying to import the module
                    if not args.dry_run:  # Skip verification in dry-run mode
                        logger.info(f"Verifying fix by importing {conftest_file}")
                        try:
                            # Try to compile the file to check for syntax errors
                            with open(conftest_file, 'r') as f:
                                code = compile(f.read(), conftest_file, 'exec')
                            logger.info(f"Verification successful: {conftest_file} compiles without syntax errors")
                            break  # Exit the attempt loop if successful
                        except SyntaxError as e:
                            logger.error(f"Verification failed: {conftest_file} still has syntax errors: {e}")
                            if attempt == max_conftest_attempts:
                                logger.error(f"Failed to fix {conftest_file} after {max_conftest_attempts} attempts")
                                return 1
                            # Continue to next attempt
                            continue
                    else:
                        # In dry-run mode, we can't verify, so just continue
                        break
                elif attempt == max_conftest_attempts:
                    logger.error(f"Failed to fix {conftest_file} after {max_conftest_attempts} attempts")
                    return 1
            
            # If we get here, we either fixed the conftest file or we're in dry-run mode
            # Continue with the next iteration to run tests again
            iteration += 1
            continue
        
        # If no files have errors but tests fail, try a more aggressive approach
        if not file_errors:
            logger.warning("Tests are failing but no specific files with errors were identified")
            
            # Try running the tests for just this directory specifically
            test_pattern = normalize_path(directory).replace(".", "/")
            fallback_test_path = f"{args.test_dir}/unit/{test_pattern}"
            
            # Extract failed test names from the error messages
            failed_tests = []
            for error in errors:
                if "::" in error:
                    test_name = error.split("::")[1].split()[0]
                    failed_tests.append(test_name)
            
            if os.path.exists(fallback_test_path):
                logger.info(f"Trying to run tests directly from {fallback_test_path}")
                
                # Try to get contents of the failed test file to provide more context
                failed_test_file_contents = ""
                try:
                    # Look for test files in the fallback test path
                    test_files = list(Path(fallback_test_path).glob("**/*.py"))
                    if test_files:
                        logger.info(f"Found {len(test_files)} test files in {fallback_test_path}")
                        for test_file in test_files:
                            with open(test_file, 'r') as f:
                                failed_test_file_contents += f"\nContents of {test_file}:\n```python\n{f.read()}\n```\n"
                except Exception as e:
                    logger.error(f"Error reading test files: {e}")
                
                # Analyze the test files to provide more context
                logger.info("Analyzing test files to understand failures")
                test_contents = analyze_test_files(fallback_test_path, failed_tests)
                
                # Add test content to the prompt for better context
                test_context = ""
                if test_contents:
                    test_context = "Here are the relevant test functions:\n\n"
                    for test_name, content in test_contents.items():
                        test_context += f"```python\n{content}\n```\n\n"
                elif failed_test_file_contents:
                    test_context = failed_test_file_contents
                
                # Create a detailed prompt with test context
                detailed_prompt = (
                    f"Fix the code in {directory} to make the tests pass. "
                    f"The tests are located at {fallback_test_path}.\n\n"
                    f"The following tests are failing:\n"
                )
                for failed_test in failed_tests:
                    detailed_prompt += f"- {failed_test}\n"
                
                detailed_prompt += f"\n{test_context}\n"
                detailed_prompt += "Examine the code and tests carefully to understand what needs to be fixed."
                
                # Try to fix the directory itself
                fix_result = fix_file_with_aider(
                    Path(directory),
                    args.model,
                    args.dry_run,
                    args.conventions_file,
                    args.verbose,
                    args.timeout,
                    False,  # check_for_urls
                    detailed_prompt,
                )
                
                if fix_result:
                    logger.info(f"Successfully applied fixes to {directory}")
                    fixes_attempted = True
                else:
                    logger.warning(f"Failed to fix {directory}")
            else:
                # Look for the actual test file
                test_files = list(Path(args.test_dir).glob(f"**/*{module_path.split('.')[-1]}*.py"))
                if test_files:
                    logger.info(f"Found test files potentially related to {directory}: {test_files}")
                    for test_file in test_files:
                        try:
                            with open(test_file, 'r') as f:
                                test_content = f.read()
                                
                            # Create a prompt using the actual test file
                            test_prompt = (
                                f"Fix the code in {directory} to make the tests pass. "
                                f"Here is the content of the test file:\n\n"
                                f"```python\n{test_content}\n```\n\n"
                                f"Examine the code and tests carefully to understand what needs to be fixed."
                            )
                            
                            # Try to fix the directory
                            fix_result = fix_file_with_aider(
                                Path(directory),
                                args.model,
                                args.dry_run,
                                args.conventions_file,
                                args.verbose,
                                args.timeout,
                                False,  # check_for_urls
                                test_prompt,
                            )
                            
                            if fix_result:
                                logger.info(f"Successfully applied fixes to {directory} using test file {test_file}")
                                fixes_attempted = True
                                break
                            else:
                                logger.warning(f"Failed to fix {directory} using test file {test_file}")
                        except Exception as e:
                            logger.error(f"Error processing test file {test_file}: {e}")
                else:
                    logger.warning(f"No test directory or files found related to {directory}")
                    logger.warning("Cannot identify specific files to fix. Will try next iteration.")
        else:
            # Step 2: Fix failing files
            logger.info(f"Fixing {len(file_errors)} files with test failures...")
            fixed_files = fix_failing_files(
                file_errors,
                args.model,
                args.dry_run,
                args.conventions_file,
                args.verbose,
                args.timeout
            )
            
            if fixed_files:
                logger.info(f"Fixed {len(fixed_files)} files in iteration {iteration}")
                fixes_attempted = True
            else:
                logger.warning("No files were fixed in this iteration")
                if iteration < args.max_iterations:
                    logger.info("Moving to next iteration...")
                else:
                    logger.warning("Maximum iterations reached without fixing all issues")
                    break
        
        iteration += 1
    
    # Final test run to verify
    logger.info("Running final test verification...")
    tests_passed, _, _ = run_tests(directory, args.test_dir, args.verbose, args.timeout)
    
    if tests_passed:
        logger.info("SUCCESS: All tests are now passing!")
        return 0
    else:
        # If we're in dry-run mode and fixes were attempted, we can't guarantee tests would fail
        if args.dry_run and fixes_attempted:
            logger.warning("DRY RUN: Tests are still failing, but would likely pass if the suggested fixes were applied")
            # Return 0 to indicate successful dry run with identified fixes
            return 0
        else:
            logger.error("FAILURE: Tests are still failing after maximum iterations")
        logger.error("FAILURE: Tests are still failing after maximum iterations")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.warning("Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1) 