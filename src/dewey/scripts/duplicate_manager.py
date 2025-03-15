"""
Identify and manage duplicate files in the ingest_data directory with collision-resistant checks.
Uses both file size and SHA-256 hash for accurate duplicate detection.
"""

import argparse
import hashlib
import logging
import os
from pathlib import Path
from typing import Dict, List, Tuple, Set
import humanize


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def calculate_file_hash(file_path: Path, block_size: int = 65536) -> str:
    """Calculate SHA-256 hash of a file with read buffering."""
    sha256 = hashlib.sha256()
    try:
        with file_path.open('rb') as f:
            for block in iter(lambda: f.read(block_size), b''):
                sha256.update(block)
        return sha256.hexdigest()
    except (IOError, PermissionError) as e:
        logger.warning(f"Could not read {file_path}: {str(e)}")
        return ""


def find_duplicates(root_dir: str) -> Dict[Tuple[str, int], List[Path]]:
    """
    Find duplicate files by size and hash.
    Returns dictionary mapping (hash, size) to list of file paths.
    """
    duplicates: Dict[Tuple[str, int], List[Path]] = {}
    total_files = 0
    total_size = 0

    root_path = Path(root_dir).expanduser().resolve()
    
    logger.info(f"Starting duplicate scan in {root_path}")
    
    if not root_path.exists():
        raise FileNotFoundError(f"Directory {root_path} does not exist")
    
    # Convert Path to string for os.walk compatibility
    for dirpath, _, filenames in os.walk(str(root_path)):
        for filename in filenames:
            file_path = Path(dirpath) / filename
            if not file_path.is_file():
                continue  # Skip directories/symlinks etc
                
            try:
                file_size = file_path.stat().st_size
                file_hash = calculate_file_hash(file_path)
                
                if not file_hash:  # Skip files we couldn't read
                    continue
                
                key = (file_hash, file_size)
                duplicates.setdefault(key, []).append(file_path)
                total_files += 1
                total_size += file_size
            except OSError as e:
                logger.error(f"Error processing {file_path}: {str(e)}")

    logger.info(f"Scanned {total_files:,} files ({humanize.naturalsize(total_size)})")
    return duplicates


def confirm_delete(files: List[Path], dry_run: bool = True) -> None:
    """Confirm and delete duplicates while preserving the oldest original."""
    if len(files) < 2:
        return

    # Sort by modification time - keep oldest file as original
    sorted_files = sorted(files, key=lambda f: f.stat().st_mtime)
    original = sorted_files[0]
    duplicates = sorted_files[1:]

    print(f"\nOriginal file ({original.stat().st_mtime:%Y-%m-%d}):")
    print(f"  {original}")

    print(f"\nPotential duplicates:")
    for dup in duplicates:
        print(f"  {dup} ({dup.stat().st_mtime:%Y-%m-%d})")

    if dry_run:
        print("\nDry run: Would delete duplicates above")
        return

    response = input("\nDelete duplicates? [y/N] ").strip().lower()
    if response != 'y':
        return

    for dup in duplicates:
        try:
            dup.unlink()
            print(f"Deleted: {dup}")
        except Exception as e:
            print(f"Error deleting {dup}: {str(e)}")


def main():
    parser = argparse.ArgumentParser(
        description="Manage duplicate files in ingest_data directory",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '--dir', 
        default='~/ingest_data',
        help="Directory to scan for duplicates"
    )
    parser.add_argument(
        '--delete', 
        action='store_true',
        help="Enable deletion mode (otherwise dry-run)"
    )
    parser.add_argument(
        '--log', 
        default='duplicate_manager.log',
        help="Log file path"
    )
    
    args = parser.parse_args()
    
    # Configure file logging
    file_handler = logging.FileHandler(args.log)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    
    try:
        duplicates = find_duplicates(args.dir)
        for key, files in duplicates.items():
            if len(files) > 1:
                confirm_delete(files, dry_run=not args.delete)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
