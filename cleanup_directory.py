#!/usr/bin/env python3

import os
import shutil
import logging
import argparse
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Constants
SRC_DIR = Path("/Users/srvo/dewey/src")
DUPLICATE_SRC_DIR = Path("/Users/srvo/dewey/src/src")
BACKUP_DIR = Path("/Users/srvo/dewey/backup/duplicate_src")

def backup_duplicate_structure():
    """Backup the duplicate src directory before making changes"""
    if DUPLICATE_SRC_DIR.exists():
        logger.info(f"Backing up {DUPLICATE_SRC_DIR} to {BACKUP_DIR}")
        BACKUP_DIR.parent.mkdir(parents=True, exist_ok=True)
        if BACKUP_DIR.exists():
            shutil.rmtree(BACKUP_DIR)
        shutil.copytree(DUPLICATE_SRC_DIR, BACKUP_DIR)
        logger.info("Backup completed")
    else:
        logger.info(f"No duplicate directory at {DUPLICATE_SRC_DIR}, skipping backup")

def fix_duplicate_src(dry_run=False):
    """Move files from src/src to src, avoiding duplicates"""
    if not DUPLICATE_SRC_DIR.exists():
        logger.info("No duplicate src directory found")
        return

    # Find all files in the duplicate src directory
    file_count = 0
    for root, dirs, files in os.walk(DUPLICATE_SRC_DIR):
        # Skip if at the top level
        if root == str(DUPLICATE_SRC_DIR):
            continue
            
        # Calculate the correct destination path by removing the duplicate src
        relative_path = os.path.relpath(root, DUPLICATE_SRC_DIR)
        dest_path = SRC_DIR / relative_path
        
        # Create the destination directory if it doesn't exist
        if not dry_run and not dest_path.exists():
            dest_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {dest_path}")
        
        # Move each file to the correct location
        for file in files:
            src_file = Path(root) / file
            dest_file = dest_path / file
            
            if dest_file.exists():
                logger.warning(f"File already exists: {dest_file}, skipping")
                continue
                
            logger.info(f"{'Would move' if dry_run else 'Moving'} {src_file} to {dest_file}")
            if not dry_run:
                shutil.move(src_file, dest_file)
                file_count += 1
    
    # Remove the empty duplicate src directory
    if not dry_run and DUPLICATE_SRC_DIR.exists():
        empty_dirs = []
        # Find all empty directories
        for root, dirs, files in os.walk(DUPLICATE_SRC_DIR, topdown=False):
            if not os.listdir(root):
                empty_dirs.append(root)
        
        # Remove empty directories
        for dir_path in empty_dirs:
            logger.info(f"Removing empty directory: {dir_path}")
            os.rmdir(dir_path)
        
        # Final check if we can remove the main duplicate src directory
        if os.path.exists(DUPLICATE_SRC_DIR) and not os.listdir(DUPLICATE_SRC_DIR):
            logger.info(f"Removing empty duplicate src directory: {DUPLICATE_SRC_DIR}")
            os.rmdir(DUPLICATE_SRC_DIR)
    
    logger.info(f"Fixed {file_count} files" if not dry_run else f"Would fix {file_count} files")

def fix_file_paths():
    """Update file paths in Python files to reflect the new structure"""
    # This would require parsing and updating import statements and file references
    # For now, we'll just log a message suggesting this as a future step
    logger.info("NOTE: You may need to update import statements in Python files to reflect the new structure")
    logger.info("This can be done with another script or manually reviewing files that have errors")

def create_init_files(dry_run=False):
    """Create __init__.py files in all directories under src"""
    count = 0
    for root, dirs, files in os.walk(SRC_DIR):
        # Skip if __init__.py already exists
        init_file = Path(root) / "__init__.py"
        if not init_file.exists():
            logger.info(f"{'Would create' if dry_run else 'Creating'} {init_file}")
            if not dry_run:
                with open(init_file, 'w') as f:
                    f.write("# Auto-generated __init__.py file\n")
                count += 1
    
    logger.info(f"{'Would create' if dry_run else 'Created'} {count} __init__.py files")

def main():
    parser = argparse.ArgumentParser(description="Clean up and fix duplicate src directory structure")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without making them")
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("Running in dry-run mode - no changes will be made")
    
    # First backup the duplicate structure
    if not args.dry_run:
        backup_duplicate_structure()
    
    # Fix the duplicate src directory
    fix_duplicate_src(args.dry_run)
    
    # Create __init__.py files
    create_init_files(args.dry_run)
    
    # Suggest fixing file paths
    fix_file_paths()
    
    if args.dry_run:
        logger.info("Dry run complete - run without --dry-run to apply changes")
    else:
        logger.info("Directory cleanup complete")

if __name__ == "__main__":
    main() 