#!/usr/bin/env python3

import fnmatch
import hashlib
import sys
import argparse
from pathlib import Path
from typing import Dict, List

from dewey.utils import get_logger

class DuplicateCheckerError(Exception):
    """Exception for duplicate checker failures."""


def find_ledger_files(start_dir: Path = Path(".")) -> Dict[str, List[Path]]:
    """Find all ledger files and calculate their hashes."""
    logger = get_logger('duplicate_checker')
    hashes: Dict[str, List[Path]] = {}
    
    try:
        for file_path in start_dir.rglob("*.journal"):
            try:
                file_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
                if file_hash not in hashes:
                    hashes[file_hash] = []
                hashes[file_hash].append(file_path)
            except Exception as e:
                logger.warning(f"Failed to process file {file_path}: {str(e)}")
                continue
                
        logger.debug(f"Found {sum(len(paths) for paths in hashes.values())} ledger files")
        return hashes
        
    except Exception as e:
        logger.exception(f"Failed to find ledger files: {str(e)}")
        raise DuplicateCheckerError(f"Failed to find ledger files: {str(e)}")


def check_duplicates(start_dir: Path = Path(".")) -> bool:
    """Check for duplicate ledger files."""
    logger = get_logger('duplicate_checker')
    
    try:
        # Find all ledger files and their hashes
        hashes = find_ledger_files(start_dir)
        
        # Find duplicates
        duplicates = {h: paths for h, paths in hashes.items() if len(paths) > 1}
        
        if duplicates:
            logger.warning(f"Found {len(duplicates)} groups of duplicate files:")
            for file_hash, paths in duplicates.items():
                logger.warning(f"\nHash: {file_hash}")
                for path in paths:
                    logger.warning(f"  - {path}")
            return True
            
        logger.info("No duplicate files found")
        return False
        
    except Exception as e:
        logger.exception(f"Failed to check for duplicates: {str(e)}")
        raise DuplicateCheckerError(f"Failed to check for duplicates: {str(e)}")


def main() -> None:
    """Main entry point for duplicate checker."""
    logger = get_logger('duplicate_checker')
    
    parser = argparse.ArgumentParser(description="Check for duplicate ledger files")
    parser.add_argument("--dir", type=Path, default=Path("."),
                       help="Directory to start searching from (default: current directory)")
    args = parser.parse_args()
    
    try:
        has_duplicates = check_duplicates(args.dir)
        if has_duplicates:
            logger.error("Duplicate files found")
            sys.exit(1)
            
    except DuplicateCheckerError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
