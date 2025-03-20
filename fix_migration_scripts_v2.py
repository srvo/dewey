#!/usr/bin/env python3
"""
Fix syntax errors in migration scripts related to string concatenation.

This script addresses the issue of unterminated string literals in migration scripts.
The specific pattern is:

```python
content = "from dewey.core.base_script import BaseScript

" + content
```

which needs to be changed to:

```python
content = "from dewey.core.base_script import BaseScript\\n\\n" + content
```

Usage:
    python fix_migration_scripts_v2.py [--dry-run] [--limit NUM_SCRIPTS]

Options:
    --dry-run       Run in dry run mode without making changes
    --limit         Limit the number of scripts to process
"""

import os
import re
import logging
import argparse
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_script(script_path, dry_run=False):
    """
    Fix syntax errors in a migration script.
    
    Args:
        script_path: Path to the migration script
        dry_run: Run in dry run mode without making changes
    
    Returns:
        bool: True if the script was fixed, False otherwise
    """
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Match the exact problematic pattern with the newlines in the string literal
        # The pattern is:
        # content = "from dewey.core.base_script import BaseScript
        #
        # " + content
        pattern = r'content = "from dewey\.core\.base_script import BaseScript\n\n" \+ content'
        
        if re.search(pattern, content):
            # This is already fixed or not the pattern we're looking for
            return False
        
        # This is the original problematic pattern with literal newlines
        problematic_pattern = r'content = "from dewey\.core\.base_script import BaseScript\n\n" \+ content'
        
        # Check if there's a different variation of the pattern
        alt_pattern = r'content = "from dewey\.core\.base_script import BaseScript\s*\n\s*\n\s*" \+ content'
        
        # If the alternate pattern is found, we need to fix it
        if re.search(alt_pattern, content, re.DOTALL):
            # Replace with the properly escaped version
            fixed_content = re.sub(
                alt_pattern,
                'content = "from dewey.core.base_script import BaseScript\\n\\n" + content',
                content,
                flags=re.DOTALL
            )
            
            if fixed_content != content:
                if not dry_run:
                    with open(script_path, 'w', encoding='utf-8') as f:
                        f.write(fixed_content)
                
                file_name = os.path.basename(script_path)
                logger.info(f"Fixed {file_name}")
                return True
        
        # Try a simpler approach - look for exactly the problematic content
        test_string = 'content = "from dewey.core.base_script import BaseScript\n\n" + content'
        replacement = 'content = "from dewey.core.base_script import BaseScript\\n\\n" + content'
        
        if test_string in content:
            fixed_content = content.replace(test_string, replacement)
            if not dry_run:
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
            
            file_name = os.path.basename(script_path)
            logger.info(f"Fixed {file_name} with direct replacement")
            return True
        
        # Try a more basic approach - replace the string with literal newlines
        search_str = '''content = "from dewey.core.base_script import BaseScript

" + content'''
        replace_str = 'content = "from dewey.core.base_script import BaseScript\\n\\n" + content'
        
        if search_str in content:
            fixed_content = content.replace(search_str, replace_str)
            if not dry_run:
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
            
            file_name = os.path.basename(script_path)
            logger.info(f"Fixed {file_name} with direct literal replacement")
            return True
            
        return False
    except Exception as e:
        file_name = os.path.basename(script_path)
        logger.error(f"Error fixing {file_name}: {str(e)}")
        return False

def find_migration_scripts(directory="migration_scripts"):
    """
    Find all migration scripts in the given directory.
    
    Args:
        directory: Directory containing migration scripts
    
    Returns:
        list: List of migration script paths
    """
    base_dir = Path(os.getcwd())
    migration_dir = base_dir / directory
    
    if not migration_dir.exists():
        logger.error(f"Directory not found: {migration_dir}")
        return []
    
    # Find all Python files in the migration directory
    script_paths = list(migration_dir.glob("*.py"))
    logger.info(f"Found {len(script_paths)} migration scripts")
    return script_paths

def main():
    """Main function to fix migration scripts."""
    parser = argparse.ArgumentParser(description="Fix syntax errors in migration scripts.")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry run mode without making changes")
    parser.add_argument("--limit", type=int, help="Limit the number of scripts to process")
    args = parser.parse_args()
    
    script_paths = find_migration_scripts()
    if not script_paths:
        return
    
    # Limit the number of scripts to process if specified
    if args.limit and args.limit > 0:
        script_paths = script_paths[:args.limit]
    
    # Process scripts in batches of 100
    batch_size = 100
    num_batches = (len(script_paths) + batch_size - 1) // batch_size
    
    fixed_count = 0
    error_count = 0
    
    for i in range(num_batches):
        logger.info(f"Processing batch {i+1}/{num_batches}")
        batch = script_paths[i*batch_size:(i+1)*batch_size]
        
        for script_path in batch:
            if fix_script(script_path, args.dry_run):
                fixed_count += 1
            else:
                error_count += 1
    
    logger.info(f"Fixed {fixed_count} scripts, encountered {error_count} errors")

if __name__ == "__main__":
    main() 