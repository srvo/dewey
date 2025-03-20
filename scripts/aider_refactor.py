#!/usr/bin/env python3
"""
Aider Refactor Script - Uses Aider to fix flake8 issues in Python files
"""

import argparse
import io
import sys
import os
import subprocess
import signal
import tempfile
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

# Try to import aider modules conditionally to handle cases where it's not installed
try:
    from aider.models import Model
    from aider.coders import Coder
    from aider.io import InputOutput
    AIDER_AVAILABLE = True
except ImportError:
    AIDER_AVAILABLE = False

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("aider_refactor")

# Configure a signal handler for timeouts
def signal_handler(signum, frame):
    """Handle timeout signal."""
    raise TimeoutError("Operation timed out")

# Register signal handlers
signal.signal(signal.SIGALRM, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Use Aider to fix flake8 issues in Python files."
    )
    parser.add_argument(
        "--dir",
        type=str,
        required=True,
        help="Directory or file to process",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="deepinfra/google/gemini-2.0-flash-001",
        help="Model to use for refactoring",
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
        default=60,
        help="Timeout in seconds for processing each file",
    )
    parser.add_argument(
        "--check-for-urls",
        action="store_true",
        help="Enable URL detection and scraping (default: disabled)",
    )
    parser.add_argument(
        "--custom-prompt",
        type=str,
        help="Custom prompt to use instead of generating one from flake8 issues",
    )
    return parser.parse_args()


def find_python_files(path: Path) -> List[Path]:
    """Find all Python files in a directory or return a single file."""
    if path.is_file() and path.suffix == ".py":
        return [path]
    elif path.is_dir():
        try:
            python_files = list(path.glob("**/*.py"))
            logger.info(f"Found {len(python_files)} Python files in {path}")
            return python_files
        except Exception as e:
            logger.error(f"Error finding Python files: {e}")
            return []
    else:
        logger.error(f"Error: {path} is not a Python file or directory")
        return []


def get_flake8_issues(file_path: Path, max_line_length: int = 88) -> List[str]:
    """Run flake8 on a file and return the issues."""
    try:
        cmd = [
            "flake8", str(file_path), f"--max-line-length={max_line_length}", 
            "--format=%(path)s:%(row)d:%(col)d: %(code)s %(text)s",
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False, timeout=30
        )
        issues = result.stdout.strip().split("\n") if result.stdout else []
        if issues == [""]:
            issues = []
        return issues
    except subprocess.TimeoutExpired:
        logger.error(f"Timed out running flake8 on {file_path}")
        return []
    except Exception as e:
        logger.error(f"Error running flake8 on {file_path}: {e}")
        return []


def fix_file_with_aider(
    file_path: Path,
    model_name: str,
    dry_run: bool = False,
    conventions_file: Optional[str] = None,
    verbose: bool = False,
    timeout: int = 60,
    check_for_urls: bool = False,
    custom_prompt: Optional[str] = None,
) -> bool:
    """Use Aider to fix issues in a file."""
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
    
    # Add conventions if available and not using a custom prompt
    if conventions_file and os.path.exists(conventions_file) and not custom_prompt:
        try:
            with open(conventions_file, 'r') as f:
                conventions = f.read()
            prompt += f"\n\nFollow these conventions when fixing the code:\n\n{conventions}"
        except Exception as e:
            logger.warning(f"Error reading conventions file: {e}")
    
    # Setup Aider
    try:
        # Create a null device for redirecting output
        null_device = tempfile.mktemp()
        
        # Make sure we have environment variables properly set for non-interactive mode
        os.environ["AIDER_NO_AUTO_COMMIT"] = "1"
        os.environ["AIDER_CHAT_HISTORY_FILE"] = os.environ.get("AIDER_CHAT_HISTORY_FILE", null_device)
        os.environ["AIDER_NO_INPUT"] = "1"
        os.environ["AIDER_QUIET"] = "1"  
        os.environ["AIDER_DISABLE_STREAMING"] = "1"
        
        # Setup the model
        model = Model(model_name)
        
        # Setup IO and disable user input to make it non-interactive
        io = InputOutput(yes=True, input_history_file=null_device)
        
        # If dry run, just report what would be done
        if dry_run:
            # Special handling for conftest.py files with syntax errors
            if "conftest.py" in str(file_path) and custom_prompt and "syntax error" in custom_prompt.lower():
                logger.info(f"[DRY RUN] Would attempt to fix syntax error in {file_path}")
                # In a real run, this might fail, so we shouldn't assume success
                if verbose:
                    logger.warning(f"[DRY RUN] Note: Syntax errors may require multiple attempts to fix completely")
                # Return True in dry-run mode for conftest files with syntax errors
                # to indicate that an attempt would be made
                return True
            elif custom_prompt:
                # For custom prompts, we would attempt to fix but can't guarantee success
                logger.info(f"[DRY RUN] Would attempt to fix issues in {file_path} with custom prompt")
                # Return True to indicate we would attempt the fix, not that it would succeed
                return True
            else:
                logger.info(f"[DRY RUN] Would fix {len(issues)} flake8 issues in {file_path}")
                return len(issues) > 0  # Return True only if there are actual issues to fix
        
        # Set alarm for timeout
        signal.alarm(timeout)
        
        try:
            # Create Aider coder instance
            logger.info(f"Creating Aider instance for {file_path}")
            coder = Coder.create(
                main_model=model,
                fnames=[str(file_path)],
                io=io,
                detect_urls=check_for_urls,  # Disable URL detection by default
            )
            
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
                    logger.info(f"Aider fixed {len(issues) - len(remaining_issues)} issues, but {len(remaining_issues)} remain")
                    for issue in remaining_issues[:3]:
                        logger.info(f"  {issue}")
                    if len(remaining_issues) > 3:
                        logger.info(f"  ... and {len(remaining_issues) - 3} more")
                return len(remaining_issues) < len(issues)  # Return True only if we fixed at least one issue
            else:
                if verbose:
                    logger.info(f"Aider successfully fixed all {len(issues)} issues in {file_path}")
                return True
        except TimeoutError:
            logger.error(f"Timed out processing {file_path}")
            signal.alarm(0)  # Turn off alarm
            return False
    except Exception as e:
        logger.error(f"Error using Aider to fix {file_path}: {e}")
        # Turn off alarm if it was set
        signal.alarm(0)
        return False
    finally:
        # Clean up temp file
        try:
            os.remove(null_device)
        except Exception:
            pass


def main():
    """Main function to run the script."""
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
    
    # Process each file
    successful = 0
    failed = 0
    
    for file_path in python_files:
        logger.info(f"Processing {file_path}...")
        try:
            if fix_file_with_aider(
                file_path,
                args.model,
                args.dry_run,
                args.conventions_file,
                args.verbose,
                args.timeout,
                args.check_for_urls,
                args.custom_prompt,
            ):
                successful += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Unexpected error processing {file_path}: {e}")
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
        logger.error(f"Unexpected error: {e}")
        sys.exit(1) 