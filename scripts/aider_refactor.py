#!/usr/bin/env python3
import argparse
import logging
import subprocess
from pathlib import Path
from aider.coders import Coder
from aider.models import Model
from aider.io import InputOutput
import sys
from datetime import datetime
import os

PROJECT_ROOT = Path("/Users/srvo/dewey")
SRC_DIR = PROJECT_ROOT / "src"
CONVENTIONS_FILE = PROJECT_ROOT / "input_data/md_files/conventions.md"
CONFIG_FILE = PROJECT_ROOT / "config/dewey.yaml"
DB_UTILS_PATH = PROJECT_ROOT / "src/dewey/core/db"
LLM_UTILS_PATH = PROJECT_ROOT / "src/dewey/llm/llm_utils.py"
DEFAULT_MODEL = "deepinfra/google/gemini-2.0-flash-001"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("aider_refactor")

def read_conventions():
    """Read the conventions.md file for context.
    
    Returns:
        The content of the conventions.md file
    """
    try:
        with open(CONVENTIONS_FILE, "r") as f:
            return f.read()
    except Exception as e:
        logger.warning(f"Could not read conventions file: {str(e)}")
        return "Conventions file not found."

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

def build_refactor_prompt(conventions_content):
    """Build the refactor prompt with conventions content.
    
    Args:
        conventions_content: The content of the conventions.md file
        
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
"""

def process_files(files: list[Path], model_name: str, logger, dry_run: bool = False):
    """Process all Python files by prompting the LLM to refactor them.
    
    Args:
        files: List of paths to Python files
        model_name: Name of the model to use
        logger: Logger instance
        dry_run: If True, don't actually modify the files
    """
    for file_path in files:
        try:
            logger.info(f"Processing {file_path}")
            if dry_run:
                continue

            # Use a null file for input history to avoid issues
            null_history = os.devnull if os.name != 'nt' else 'NUL'
            io = InputOutput(yes=False, input_history_file=null_history)
            
            # Get the refactoring prompt
            refactor_prompt = f"""Refactor this file to adhere to Dewey conventions:
                
1. All modules should inherit from BaseScript
2. Use self.logger for logging instead of creating a logger
3. Access configuration via self.get_config_value() 
4. Each script should implement a run() method
5. Use Google-style docstrings
6. Add proper type hints
                """
            
            # Initialize model
            model = Model(model_name)
            
            # Create coder with the file
            coder = Coder.create(
                main_model=model,
                fnames=[str(file_path)],
                io=io
            )
            
            # Run refactoring - avoid command confusion
            coder.run(refactor_prompt)
            
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Refactor Python files to match project conventions")
    parser.add_argument('--dry-run', action='store_true', help="Don't actually modify files")
    parser.add_argument('--dir', type=str, help="Directory containing files to refactor")
    parser.add_argument('--file', type=str, help="Single file to refactor")
    parser.add_argument('--model', type=str, default=DEFAULT_MODEL, help="Model to use for refactoring")
    args = parser.parse_args()
    
    # Check if either --dir or --file is provided
    if args.dir is None and args.file is None:
        logger.error("Either --dir or --file must be specified")
        sys.exit(1)
    
    # Get target path
    target_path = None
    if args.dir:
        target_path = Path(args.dir)
    else:
        target_path = Path(args.file)
    
    # Find Python files
    python_files = find_python_files(target_path)
    
    # Process files
    logger.info(f"Found {len(python_files)} Python files to process")
    
    # Try to get conventions from file
    try:
        with open('input_data/md_files/conventions.md', 'r') as f:
            conventions = f.read()
            logger.info(f"Loaded conventions from file: {len(conventions)} bytes")
    except FileNotFoundError:
        logger.warning("Could not read conventions file")
    
    # Process files
    process_files(python_files, args.model, logger, args.dry_run)
    
    logger.info("Refactoring complete")

if __name__ == "__main__":
    main() 