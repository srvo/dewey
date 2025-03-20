#!/usr/bin/env python3
"""
Fix script extensions
Renames migration script files from *.py.py to *.py
"""

import os
import sys
import glob
import logging
import argparse
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

MIGRATION_SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migration_scripts")

def rename_script_files(dry_run=False):
    """Rename all *.py.py files to *.py"""
    if not os.path.exists(MIGRATION_SCRIPTS_DIR):
        logger.error(f"Migration scripts directory not found: {MIGRATION_SCRIPTS_DIR}")
        return 0
    
    # Find all *.py.py files
    script_paths = glob.glob(os.path.join(MIGRATION_SCRIPTS_DIR, "*.py.py"))
    
    if not script_paths:
        logger.info("No files with incorrect extensions found.")
        return 0
    
    logger.info(f"Found {len(script_paths)} files with incorrect extensions")
    
    renamed_count = 0
    for script_path in script_paths:
        base_path = script_path[:-3]  # Remove the extra .py
        
        if dry_run:
            logger.info(f"Would rename {os.path.basename(script_path)} to {os.path.basename(base_path)}")
            renamed_count += 1
            continue
        
        try:
            # Check if destination exists
            if os.path.exists(base_path):
                logger.warning(f"Destination file {base_path} already exists, backing it up")
                backup_path = f"{base_path}.bak"
                shutil.move(base_path, backup_path)
            
            # Rename file
            shutil.move(script_path, base_path)
            logger.info(f"Renamed {os.path.basename(script_path)} to {os.path.basename(base_path)}")
            renamed_count += 1
            
            # Also fix the script content - replace any self-references to *.py.py with *.py
            with open(base_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Fix NEW_FILE_PATH assignments
            if '.py.py' in content:
                fixed_content = content.replace('.py.py', '.py')
                with open(base_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                logger.info(f"Fixed internal path references in {os.path.basename(base_path)}")
            
        except Exception as e:
            logger.error(f"Error renaming {script_path}: {e}")
    
    return renamed_count

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Fix migration script file extensions")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually rename files, just log what would happen")
    
    args = parser.parse_args()
    
    renamed_count = rename_script_files(args.dry_run)
    
    if args.dry_run:
        logger.info(f"Would rename {renamed_count} files")
    else:
        logger.info(f"Renamed {renamed_count} files")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 