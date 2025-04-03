#!/usr/bin/env python3
"""Aider Refactor Script - Uses Aider to fix flake8 issues in Python files."""

import argparse
import contextlib
import logging
import os
import re
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Never

# Try to import aider modules conditionally to handle cases where it's not installed
try:
    from aider.coders import Coder
    from aider.io import InputOutput
    from aider.models import Model

    AIDER_AVAILABLE = True
except ImportError:
    AIDER_AVAILABLE = False
    sys.exit(1)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("aider_refactor")

# Global variables for persistent session
GLOBAL_CODER = None
GLOBAL_CHAT_HISTORY_FILE = None


# Configure a signal handler for timeouts
def signal_handler(signum, frame) -> Never:
    """Handle timeout signal."""
    logger.error("Timeout reached")
    msg = "Timeout reached"
    raise TimeoutError(msg)


# Register signal handlers
signal.signal(signal.SIGALRM, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Use Aider to refactor code and generate tests",
    )
    parser.add_argument("--dir", required=True, help="Directory or file to process")
    parser.add_argument("--model", default="gpt-4-turbo", help="Model to use")
    parser.add_argument("--dry-run", action="store_true", help="Don't make any changes")
    parser.add_argument("--conventions-file", help="File containing coding conventions")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Timeout in seconds for processing each file",
    )
    parser.add_argument(
        "--check-for-urls", action="store_true", help="Check for URLs in prompts",
    )
    parser.add_argument("--custom-prompt", help="Custom prompt for Aider")
    parser.add_argument(
        "--persist-session", action="store_true", help="Use a persistent Aider session",
    )
    parser.add_argument(
        "--session-dir",
        help="Directory to store persistent session files",
        default=".aider",
    )
    return parser.parse_args()


def find_python_files(path: Path) -> list[Path]:
    """Find all Python files in a directory or return a single file."""
    if path.is_file() and path.suffix == ".py":
        return [path]
    if path.is_dir():
        try:
            python_files = list(path.glob("**/*.py"))
            logger.info("Found %s Python files in %s", len(python_files), path)
            return python_files
        except Exception as e:
            logger.exception("Error finding Python files: %s", e)
            return []
    else:
        logger.error("Error: %s is not a Python file or directory", path)
        return []


def get_flake8_issues(file_path: Path, max_line_length: int = 88) -> list[str]:
    """Run flake8 on a file and return the issues."""
    try:
        cmd = [
            "flake8",
            str(file_path),
            f"--max-line-length={max_line_length}",
            "--format=%(path)s:%(row)d:%(col)d: %(code)s %(text)s",
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False, timeout=30,
        )
        issues = result.stdout.strip().split("\n") if result.stdout else []
        if issues == [""]:
            issues = []
        return issues
    except subprocess.TimeoutExpired:
        logger.exception(f"Timed out running flake8 on {file_path}")
        return []
    except Exception as e:
        logger.exception(f"Error running flake8 on {file_path}: {e}")
        return []


def initialize_persistent_session(args):
    """Initialize a persistent Aider session."""
    global GLOBAL_CODER, GLOBAL_CHAT_HISTORY_FILE

    if GLOBAL_CODER is not None:
        return GLOBAL_CODER

    session_dir = Path(args.session_dir)
    if not session_dir.exists():
        session_dir.mkdir(parents=True)

    chat_history_dir = session_dir / "chat_history"
    if not chat_history_dir.exists():
        chat_history_dir.mkdir(parents=True)

    # Create a chat history file for this specific directory/file
    target_path = Path(args.dir).resolve()
    safe_name = re.sub(r"[^\w-]", "_", str(target_path))
    GLOBAL_CHAT_HISTORY_FILE = str(chat_history_dir / f"{safe_name}.json")

    # Set up environment variables
    os.environ["AIDER_NO_AUTO_COMMIT"] = "1"
    os.environ["AIDER_CHAT_HISTORY_FILE"] = GLOBAL_CHAT_HISTORY_FILE
    os.environ["AIDER_NO_INPUT"] = "1"
    os.environ["AIDER_QUIET"] = "1"
    os.environ["AIDER_DISABLE_STREAMING"] = "1"

    # Setup model and IO
    model = Model(args.model)
    io = InputOutput(yes=True, input_history_file=GLOBAL_CHAT_HISTORY_FILE)

    # Create the coder instance
    try:
        # Create an initial list of files to include
        initial_files = []
        python_files = find_python_files(target_path)
        if python_files:
            # Start with the first file if there are many
            initial_files.append(str(python_files[0]))

        logger.info(
            f"Initializing persistent Aider session with {len(initial_files)} files",
        )
        GLOBAL_CODER = Coder.create(
            main_model=model,
            fnames=initial_files,
            io=io,
            detect_urls=args.check_for_urls,
        )
        return GLOBAL_CODER
    except Exception as e:
        logger.exception(f"Error creating persistent Aider session: {e}")
        GLOBAL_CODER = None
        return None


def fix_file_with_aider(
    file_path: Path,
    model_name: str,
    dry_run: bool = False,
    conventions_file: str | None = None,
    verbose: bool = False,
    timeout: int = 60,
    check_for_urls: bool = False,
    custom_prompt: str | None = None,
    persist_session: bool = False,
    session_args=None,
) -> bool:
    """Use Aider to fix issues in a file."""
    global GLOBAL_CODER

    # Check if file_path is a directory
    if file_path.is_dir():
        if verbose:
            logger.info(f"Processing directory {file_path}")

        # Find Python files in the directory
        python_files = list(file_path.glob("**/*.py"))
        if not python_files:
            logger.warning(f"No Python files found in {file_path}")
            return False

        # If the directory contains Python files and we have a custom prompt,
        # process the first few files
        if custom_prompt and python_files:
            # Always process __init__.py first if it exists
            init_file = file_path / "__init__.py"
            if init_file.exists() and init_file in python_files:
                if fix_file_with_aider(
                    init_file,
                    model_name,
                    dry_run,
                    conventions_file,
                    verbose,
                    timeout,
                    check_for_urls,
                    custom_prompt,
                    persist_session,
                    session_args,
                ):
                    return True

            # Try up to 3 Python files
            for py_file in python_files[:3]:
                if py_file != init_file:  # Skip if we already processed init_file
                    if fix_file_with_aider(
                        py_file,
                        model_name,
                        dry_run,
                        conventions_file,
                        verbose,
                        timeout,
                        check_for_urls,
                        custom_prompt,
                        persist_session,
                        session_args,
                    ):
                        return True

            return False

        logger.warning(
            f"Skipping directory {file_path} - need a custom prompt to process directories",
        )
        return False

    # From here on, we're processing a single file

    # Get flake8 issues if we don't have a custom prompt
    issues = []
    if not custom_prompt:
        issues = get_flake8_issues(file_path)
        if not issues:
            if verbose:
                logger.info(f"No flake8 issues found in {file_path}")
            return True

        if verbose:
            logger.info(f"Found {len(issues)} flake8 issues in {file_path}:")
            for issue in issues[:5]:
                logger.info(f"  {issue}")
            if len(issues) > 5:
                logger.info(f"  ... and {len(issues) - 5} more")

        # Create a prompt for Aider
        prompt = "Fix the following flake8 issues in this file:\n\n"
        for issue in issues:
            prompt += f"- {issue}\n"
    else:
        # Use the provided custom prompt
        prompt = custom_prompt
        if verbose:
            logger.info(f"Using custom prompt for {file_path}")

    # Add test framework context to the prompt
    if "test failures" in prompt.lower() or "failed tests" in prompt.lower():
        test_context = """
## Test System Context
- Tests are run using pytest
- Test files are located in the 'tests/' directory
- Test modules follow the pattern 'test_*.py'
- Each test function begins with 'test_'
- Fixtures may be defined in conftest.py files
- Failed tests may include assertion errors or runtime errors
- The code should conform to flake8 and mypy standards
"""
        prompt += test_context

    # Add conventions if available and not using a custom prompt
    if conventions_file and os.path.exists(conventions_file) and not custom_prompt:
        try:
            with open(conventions_file, encoding="utf-8") as f:
                conventions = f.read()
            prompt += (
                f"\n\nFollow these conventions when fixing the code:\n\n{conventions}"
            )
        except Exception as e:
            logger.warning(f"Error reading conventions file: {e}")

    # If dry run, just report what would be done
    if dry_run:
        # Special handling for conftest.py files with syntax errors
        if (
            "conftest.py" in str(file_path)
            and custom_prompt
            and "syntax error" in custom_prompt.lower()
        ):
            logger.info(f"[DRY RUN] Would attempt to fix syntax error in {file_path}")
            # In a real run, this might fail, so we shouldn't assume success
            if verbose:
                logger.warning(
                    "[DRY RUN] Note: Syntax errors may require multiple attempts to fix completely",
                )
            # Return True in dry-run mode for conftest files with syntax errors
            # to indicate that an attempt would be made
            return True
        if custom_prompt:
            # For custom prompts, we would attempt to fix but can't guarantee success
            logger.info(
                f"[DRY RUN] Would attempt to fix issues in {file_path} with custom prompt",
            )
            # Return True to indicate we would attempt the fix, not that it would succeed
            return True
        logger.info(f"[DRY RUN] Would fix {len(issues)} flake8 issues in {file_path}")
        return len(issues) > 0  # Return True only if there are actual issues to fix

    # Set alarm for timeout
    signal.alarm(timeout)

    try:
        # Use persistent coder if requested
        if persist_session and session_args:
            coder = initialize_persistent_session(session_args)
            if coder is None:
                # Fall back to creating a new instance
                logger.warning("Falling back to creating a new Aider instance")
                persist_session = False

        if not persist_session or GLOBAL_CODER is None:
            # Create a null device for redirecting output
            null_device = tempfile.mktemp()

            # Make sure we have environment variables properly set for non-interactive mode
            os.environ["AIDER_NO_AUTO_COMMIT"] = "1"
            os.environ["AIDER_CHAT_HISTORY_FILE"] = os.environ.get(
                "AIDER_CHAT_HISTORY_FILE", null_device,
            )
            os.environ["AIDER_NO_INPUT"] = "1"
            os.environ["AIDER_QUIET"] = "1"
            os.environ["AIDER_DISABLE_STREAMING"] = "1"

            # Setup the model
            model = Model(model_name)

            # Setup IO and disable user input to make it non-interactive
            io = InputOutput(yes=True, input_history_file=null_device)

            # Create Aider coder instance
            logger.info(f"Creating Aider instance for {file_path}")
            coder = Coder.create(
                main_model=model,
                fnames=[str(file_path)],
                io=io,
                detect_urls=check_for_urls,  # Disable URL detection by default
            )
        else:
            # Use the existing coder but add the current file if it's not already included
            logger.info(f"Using persistent Aider session for {file_path}")
            coder = GLOBAL_CODER

            # Different coders in Aider have different APIs
            # WholeFileCoder doesn't have add_files, but others do
            file_str = str(file_path)
            try:
                # Check the coder type to determine how to handle it
                if hasattr(coder, "add_files"):
                    # For coders that support add_files (like EditorCoder)
                    # Check if the file is already in the repo map
                    has_file = False
                    try:
                        # Try different ways to check if the file is in the repo map
                        # Method 1: Check if repo_map.files exists
                        if (
                            (
                                hasattr(coder.repo_map, "files")
                                and file_str not in coder.repo_map.files
                            )
                            or (
                                hasattr(coder.repo_map, "get_all_files")
                                and file_str not in coder.repo_map.get_all_files()
                            )
                            or (
                                (
                                    hasattr(coder.repo_map, "keys")
                                    and file_str not in list(coder.repo_map.keys())
                                )
                                or (
                                    isinstance(coder.repo_map, dict)
                                    and file_str not in coder.repo_map
                                )
                            )
                        ):
                            has_file = False
                        else:
                            has_file = True
                    except Exception:
                        has_file = False

                    if not has_file:
                        logger.info(f"Adding {file_path} to the persistent session")
                        coder.add_files([file_str])
                else:
                    # For WholeFileCoder or other coders without add_files
                    # We need to create a new coder instance each time
                    logger.info(
                        f"Current coder doesn't support add_files, using direct file content for {file_path}",
                    )

                    # If we're using WholeFileCoder, it typically works with file content directly
                    # We don't need to add files, as it will process the current file content
                    if not hasattr(coder, "repo_map"):
                        logger.info(
                            f"Coder doesn't have a repo_map, assuming WholeFileCoder for {file_path}",
                        )
                        # WholeFileCoder works differently - it already has the file loaded
                    else:
                        # We have a coder with repo_map but no add_files, which is unexpected
                        # Log this unusual situation
                        logger.warning(
                            f"Unexpected coder type - has repo_map but no add_files method for {file_path}",
                        )

                        # If the file isn't in the coder's context yet, we'll need to recreate it
                        # This is a fallback case

                        # Create a new coder instance just for this file
                        logger.info(f"Creating new coder instance for {file_path}")
                        # Turn off the persistent session for this run
                        persist_session = False
                        null_device = tempfile.mktemp()
                        model = Model(model_name)
                        io = InputOutput(yes=True, input_history_file=null_device)
                        coder = Coder.create(
                            main_model=model,
                            fnames=[str(file_path)],
                            io=io,
                            detect_urls=check_for_urls,
                        )
            except Exception as e:
                logger.warning(f"Error checking/adding file: {e}")
                # Attempt to recreate the coder for just this file as fallback
                try:
                    logger.info(
                        f"Falling back to creating a new coder instance for {file_path}",
                    )
                    null_device = tempfile.mktemp()
                    model = Model(model_name)
                    io = InputOutput(yes=True, input_history_file=null_device)
                    coder = Coder.create(
                        main_model=model,
                        fnames=[str(file_path)],
                        io=io,
                        detect_urls=check_for_urls,
                    )
                    persist_session = False  # Disable persistence for this run
                except Exception as create_error:
                    logger.exception(f"Failed to create fallback coder: {create_error}")
                    raise

        # Run Aider to fix the issues
        logger.info(f"Running Aider on {file_path}")
        coder.run(with_message=prompt)

        # Turn off alarm
        signal.alarm(0)

        # For custom prompts, we can't directly verify if it was successful
        # Return True if we made it this far without errors
        if custom_prompt:
            return True

        # Check if issues were fixed
        remaining_issues = get_flake8_issues(file_path)
        if remaining_issues:
            if verbose:
                logger.info(
                    f"Aider fixed {len(issues) - len(remaining_issues)} issues, but {len(remaining_issues)} remain",
                )
                for issue in remaining_issues[:3]:
                    logger.info(f"  {issue}")
                if len(remaining_issues) > 3:
                    logger.info(f"  ... and {len(remaining_issues) - 3} more")
            return len(remaining_issues) < len(
                issues,
            )  # Return True only if we fixed at least one issue
        if verbose:
            logger.info(
                f"Aider successfully fixed all {len(issues)} issues in {file_path}",
            )
        return True
    except TimeoutError:
        logger.exception(f"Timed out processing {file_path}")
        signal.alarm(0)  # Turn off alarm
        return False
    except Exception as e:
        logger.exception(f"Error using Aider to fix {file_path}: {e}")
        # Turn off alarm if it was set
        signal.alarm(0)
        return False
    finally:
        # Clean up temp file if we created one
        if not persist_session and "null_device" in locals():
            with contextlib.suppress(Exception):
                os.remove(null_device)


def main() -> None:
    """Execute main functions to run the script."""
    args = parse_args()
    path = Path(args.dir)

    if not path.exists():
        logger.error(f"Error: {path} does not exist")
        sys.exit(1)

    # Find Python files
    python_files = find_python_files(path)
    logger.info(f"Found {len(python_files)} Python files to process")

    if not python_files:
        logger.warning(f"No Python files found in {path}")
        sys.exit(0)

    # For directories, we need to handle special cases
    if path.is_dir() and args.custom_prompt:
        # When a custom prompt is provided for a directory, we'll
        # first create a repository context using repomix if available
        try:
            # Try to import repomix if available
            import repomix

            # Get repository context for the directory
            logger.info(f"Generating repository context for {path} using repomix")
            repo_context = repomix.get_repo_map(str(path))

            # Add file summaries to the custom prompt
            enhanced_prompt = args.custom_prompt + "\n\n## Repository Context\n\n"

            # Add file summaries
            file_summaries = []
            for file_path in repo_context.get("python_files", []):
                if os.path.exists(file_path):
                    try:
                        summary = repomix.summarize_file(file_path)
                        enhanced_prompt += f"### {file_path}\n{summary}\n\n"
                        file_summaries.append({"path": file_path, "summary": summary})
                    except Exception as e:
                        logger.exception(f"Error summarizing file {file_path}: {e}")

            logger.info(
                f"Enhanced prompt with summaries of {len(file_summaries)} files",
            )

            # Set the enhanced prompt
            custom_prompt = enhanced_prompt
        except ImportError:
            logger.info("Repomix not available; using custom prompt as is")
            custom_prompt = args.custom_prompt
        except Exception as e:
            logger.exception(f"Error generating repository context: {e}")
            custom_prompt = args.custom_prompt
    else:
        custom_prompt = args.custom_prompt

    # Initialize persistent session if requested
    if args.persist_session:
        logger.info("Using persistent Aider session")
        initialize_persistent_session(args)

    # Process each file
    successful = 0
    failed = 0

    for file_path in python_files:
        logger.info(f"Processing {file_path}...")
        try:
            # We don't process directories directly, only individual files
            if file_path.is_dir():
                logger.warning(
                    f"Skipping directory {file_path} - only processing individual files",
                )
                continue

            if fix_file_with_aider(
                file_path,
                args.model,
                args.dry_run,
                args.conventions_file,
                args.verbose,
                args.timeout,
                args.check_for_urls,
                custom_prompt,
                args.persist_session,
                args,
            ):
                successful += 1
            else:
                failed += 1
        except Exception as e:
            logger.exception(f"Unexpected error processing {file_path}: {e}")
            failed += 1

    # Print summary
    logger.info(f"\nProcessed {len(python_files)} Python files")
    logger.info(f"Successfully fixed {successful} files")
    logger.info(f"Failed to fix {failed} files")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)
