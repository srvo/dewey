#!/usr/bin/env python3
"""
Reorganize migration scripts into the proper directory structure.

This script:
1. Loads migration scripts from /Users/srvo/dewey/migration_scripts
2. Analyzes each script to determine the appropriate module/directory
3. Places the scripts in the correct structure in /Users/srvo/dewey/src
4. Fixes structural issues like the duplicate /Users/srvo/dewey/src/src

Usage:
    python reorganize_scripts.py [--dry-run] [--verbose]

Options:
    --dry-run       Run without making any file changes (just print what would happen)
    --verbose       Print detailed information about each script
"""

import os
import re
import sys
import shutil
import logging
import argparse
import importlib.util
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("reorganize.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Constants
MIGRATION_SCRIPTS_DIR = "/Users/srvo/dewey/migration_scripts"
SRC_DIR = "/Users/srvo/dewey/src"
TARGET_DIR = "/Users/srvo/dewey/src"  # This will be the new structure
BACKUP_DIR = "/Users/srvo/dewey/backup_src"

# Module mapping based on conventions
MODULE_MAPPING = {
    # Core modules
    "accounting": "core/accounting",
    "crm": "core/crm",
    "research": "core/research",
    "personal": "core/personal",
    "automation": "core/automation",
    "base_script": "core",
    "engines": "core/engines",
    "bookkeeping": "core/bookkeeping",
    
    # LLM modules
    "llm": "llm",
    "prompts": "llm/prompts",
    "api_clients": "llm/api_clients",
    "agents": "llm/agents",
    
    # Pipeline modules
    "pipeline": "pipeline",
    
    # UI modules
    "ui": "ui",
    "screens": "ui/screens",
    "components": "ui/components",
    
    # Utils 
    "utils": "utils",
    
    # Tests
    "test": "tests",
    "tests": "tests",
    
    # Default for unmapped files - will be analyzed further
    "default": "core"
}

# Keywords to help identify module classification
MODULE_KEYWORDS = {
    "core/accounting": ["accounting", "ledger", "transaction", "balance", "invoice", "receipt"],
    "core/crm": ["crm", "customer", "client", "relation", "contact"],
    "core/research": ["research", "analysis", "investment", "performance", "portfolio", "market"],
    "core/personal": ["personal", "user", "profile", "preference"],
    "core/automation": ["automation", "workflow", "trigger", "action", "schedule", "cron"],
    "core/engines": ["engine", "search", "api", "integration"],
    "core/bookkeeping": ["bookkeeping", "category", "transaction", "verify"],
    "llm": ["llm", "language model", "gpt", "embedding", "token", "prompt", "generation"],
    "llm/prompts": ["prompt", "template", "instruction"],
    "llm/api_clients": ["api", "client", "connection", "deep infra"],
    "llm/agents": ["agent", "assistant", "autonomous"],
    "pipeline": ["pipeline", "etl", "extract", "transform", "load"],
    "ui/screens": ["screen", "page", "view", "route"],
    "ui/components": ["component", "button", "input", "form", "widget"],
    "utils": ["util", "helper", "common", "shared"],
    "tests": ["test", "assert", "fixture", "mock"]
}

def backup_existing_structure():
    """Create a backup of the existing src directory structure."""
    if os.path.exists(BACKUP_DIR):
        logger.info(f"Removing existing backup directory: {BACKUP_DIR}")
        shutil.rmtree(BACKUP_DIR)
        
    if os.path.exists(SRC_DIR):
        logger.info(f"Creating backup of src directory to: {BACKUP_DIR}")
        shutil.copytree(SRC_DIR, BACKUP_DIR)
    else:
        logger.warning(f"Source directory does not exist: {SRC_DIR}")

def fix_structure_issues():
    """Fix structural issues like duplicate src directory."""
    duplicate_src = os.path.join(SRC_DIR, "src")
    if os.path.exists(duplicate_src):
        logger.info(f"Found duplicate src directory: {duplicate_src}")
        
        # Get all files and directories in the duplicate src directory
        for item in os.listdir(duplicate_src):
            src_item = os.path.join(duplicate_src, item)
            dest_item = os.path.join(SRC_DIR, item)
            
            if os.path.exists(dest_item):
                logger.warning(f"Item already exists in target location, merging: {dest_item}")
                
                # If both are directories, merge them
                if os.path.isdir(src_item) and os.path.isdir(dest_item):
                    for sub_item in os.listdir(src_item):
                        src_sub_item = os.path.join(src_item, sub_item)
                        dest_sub_item = os.path.join(dest_item, sub_item)
                        
                        if os.path.exists(dest_sub_item):
                            logger.warning(f"Subitem already exists, skipping: {dest_sub_item}")
                        else:
                            if os.path.isdir(src_sub_item):
                                shutil.copytree(src_sub_item, dest_sub_item)
                            else:
                                shutil.copy2(src_sub_item, dest_sub_item)
                            logger.info(f"Moved {src_sub_item} to {dest_sub_item}")
                else:
                    logger.warning(f"Skipping item due to conflict: {src_item}")
            else:
                # Move the item to the correct location
                if os.path.isdir(src_item):
                    shutil.copytree(src_item, dest_item)
                else:
                    shutil.copy2(src_item, dest_item)
                logger.info(f"Moved {src_item} to {dest_item}")
        
        # After moving everything, rename the duplicate src directory to a backup
        backup_duplicate = os.path.join(SRC_DIR, "old_src_backup")
        logger.info(f"Renaming duplicate src directory to: {backup_duplicate}")
        os.rename(duplicate_src, backup_duplicate)

def analyze_script_content(content: str) -> str:
    """
    Analyze script content to determine appropriate module.
    
    Args:
        content: Script content as string
        
    Returns:
        str: Module path for the script
    """
    # Look for import statements as hints
    import_matches = re.findall(r'^\s*from\s+dewey\.([a-zA-Z0-9_.]+)\s+import', content, re.MULTILINE)
    if import_matches:
        # Get the first segment of the import path which should represent the module
        for import_path in import_matches:
            parts = import_path.split('.')
            if parts[0] in MODULE_MAPPING:
                return MODULE_MAPPING[parts[0]]
    
    # Look for class definitions with docstrings
    class_matches = re.findall(r'class\s+([a-zA-Z0-9_]+).*?\s*"""(.*?)"""', content, re.DOTALL)
    if class_matches:
        for class_name, docstring in class_matches:
            # Check docstring for module keywords
            for module, keywords in MODULE_KEYWORDS.items():
                for keyword in keywords:
                    if keyword.lower() in docstring.lower():
                        return module
    
    # Look for specific functions that indicate purpose
    for module, keywords in MODULE_KEYWORDS.items():
        for keyword in keywords:
            # Check if keyword appears prominently in the file
            if keyword.lower() in content.lower():
                # Count the number of occurrences to gauge relevance
                count = content.lower().count(keyword.lower())
                if count >= 2:  # Arbitrary threshold
                    return module
    
    # Look for file type hints in comments
    if "# Script type: " in content:
        type_match = re.search(r'# Script type:\s*([a-zA-Z0-9_/]+)', content)
        if type_match:
            script_type = type_match.group(1).lower()
            for module_key, module_path in MODULE_MAPPING.items():
                if module_key in script_type:
                    return module_path
    
    # Try to infer from filename
    filename_match = re.search(r'filename\s*=\s*[\'"]([^\'"]+)[\'"]', content, re.IGNORECASE)
    if filename_match:
        filename = filename_match.group(1)
        if "test" in filename.lower():
            return "tests"
        for module, keywords in MODULE_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in filename.lower():
                    return module
    
    # Default to core if no strong indicators
    return MODULE_MAPPING["default"]

def determine_target_location(script_path: str) -> str:
    """
    Determine the target location for a script based on its content.
    
    Args:
        script_path: Path to the script
        
    Returns:
        str: Target path for the script in the new structure
    """
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract the base filename
        filename = os.path.basename(script_path)
        
        # Special naming conventions for unit tests
        if filename.startswith("test_"):
            return os.path.join(TARGET_DIR, "tests", filename)
        
        # Check for migration scripts (usually manage database migrations)
        if "migration" in filename.lower() or "migrate" in filename.lower():
            return os.path.join(TARGET_DIR, "core", "migrations", filename)
        
        # Analyze content to determine module
        module_path = analyze_script_content(content)
        
        # Return the full target path
        return os.path.join(TARGET_DIR, module_path, filename)
    
    except Exception as e:
        logger.error(f"Error determining target for {script_path}: {str(e)}")
        # Default location for files that couldn't be analyzed
        return os.path.join(TARGET_DIR, "unclassified", os.path.basename(script_path))

def list_migration_scripts() -> List[str]:
    """
    List all migration scripts in the migration scripts directory.
    
    Returns:
        List[str]: List of migration script paths
    """
    if not os.path.exists(MIGRATION_SCRIPTS_DIR):
        logger.error(f"Migration scripts directory not found: {MIGRATION_SCRIPTS_DIR}")
        return []
    
    script_paths = []
    for root, _, files in os.walk(MIGRATION_SCRIPTS_DIR):
        for file in files:
            if file.endswith('.py'):
                script_paths.append(os.path.join(root, file))
    
    logger.info(f"Found {len(script_paths)} migration scripts")
    return script_paths

def move_script(source_path: str, target_path: str, dry_run: bool = False) -> bool:
    """
    Move a script from source to target location.
    
    Args:
        source_path: Source file path
        target_path: Target file path
        dry_run: If True, don't actually move the file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create target directory if it doesn't exist
        target_dir = os.path.dirname(target_path)
        if not os.path.exists(target_dir):
            if not dry_run:
                os.makedirs(target_dir, exist_ok=True)
            logger.info(f"Created directory: {target_dir}")
        
        # Check if target file already exists
        if os.path.exists(target_path):
            logger.warning(f"Target file already exists: {target_path}")
            return False
        
        # Move the file
        if not dry_run:
            shutil.copy2(source_path, target_path)
            logger.info(f"Moved {source_path} to {target_path}")
        else:
            logger.info(f"[DRY RUN] Would move {source_path} to {target_path}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error moving {source_path} to {target_path}: {str(e)}")
        return False

def init_directory_structure(dry_run: bool = False):
    """
    Initialize the directory structure based on the module mapping.
    
    Args:
        dry_run: If True, don't actually create directories
    """
    # Create base directories
    for module_path in set(MODULE_MAPPING.values()):
        full_path = os.path.join(TARGET_DIR, module_path)
        if not os.path.exists(full_path):
            if not dry_run:
                os.makedirs(full_path, exist_ok=True)
            logger.info(f"Created directory: {full_path}")
    
    # Create special directories
    special_dirs = ["unclassified", "core/migrations"]
    for special_dir in special_dirs:
        full_path = os.path.join(TARGET_DIR, special_dir)
        if not os.path.exists(full_path):
            if not dry_run:
                os.makedirs(full_path, exist_ok=True)
            logger.info(f"Created directory: {full_path}")

def create_init_files(dry_run: bool = False):
    """
    Create __init__.py files in all directories.
    
    Args:
        dry_run: If True, don't actually create files
    """
    # Walk through the target directory structure
    for root, dirs, _ in os.walk(TARGET_DIR):
        # Skip certain directories
        if "__pycache__" in root or ".git" in root:
            continue
        
        # Create __init__.py in each directory
        init_path = os.path.join(root, "__init__.py")
        if not os.path.exists(init_path):
            if not dry_run:
                with open(init_path, 'w', encoding='utf-8') as f:
                    f.write(f'"""\nPackage initialization for {os.path.relpath(root, TARGET_DIR)}\n"""\n')
                logger.info(f"Created __init__.py file: {init_path}")
            else:
                logger.info(f"[DRY RUN] Would create __init__.py file: {init_path}")

def main():
    """Main function to reorganize scripts."""
    parser = argparse.ArgumentParser(description="Reorganize migration scripts into proper directory structure.")
    parser.add_argument("--dry-run", action="store_true", help="Run without making any file changes")
    parser.add_argument("--verbose", action="store_true", help="Print detailed information about each script")
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("Starting script reorganization")
    
    # Backup existing structure
    if not args.dry_run:
        backup_existing_structure()
    
    # Fix structure issues
    if not args.dry_run:
        fix_structure_issues()
    
    # Initialize directory structure
    init_directory_structure(args.dry_run)
    
    # List all migration scripts
    script_paths = list_migration_scripts()
    
    # Process each script
    success_count = 0
    for script_path in script_paths:
        target_path = determine_target_location(script_path)
        if move_script(script_path, target_path, args.dry_run):
            success_count += 1
    
    # Create __init__.py files
    create_init_files(args.dry_run)
    
    logger.info(f"Reorganization complete: {success_count}/{len(script_paths)} scripts processed")
    
    # Print summary
    if not args.dry_run:
        logger.info("Summary of changes:")
        logger.info(f"- Moved {success_count} scripts to their proper locations")
        logger.info(f"- Created directory structure based on project conventions")
        logger.info(f"- Added __init__.py files to all directories")
        logger.info(f"- Fixed structural issues (like duplicate src directory)")
    else:
        logger.info("[DRY RUN] No actual changes were made")

if __name__ == "__main__":
    main() 