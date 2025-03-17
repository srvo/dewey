import fnmatch
import hashlib
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def find_ledger_files() -> dict[str, list[str]]:
    """Find all ledger files and calculate their hashes.

    Returns
    -------
        A dictionary where keys are file hashes and values are lists of
        filepaths with that hash.

    """
    hashes: dict[str, list[str]] = {}
    for root, _dirnames, filenames in os.walk("."):
        for filename in fnmatch.filter(filenames, "*.journal"):
            filepath = os.path.join(root, filename)
            with open(filepath, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
                if file_hash not in hashes:
                    hashes[file_hash] = []
                hashes[file_hash].append(filepath)
    return hashes


def check_duplicates() -> bool:
    """Check for duplicate ledger files.

    Returns
    -------
        True if duplicate files were found, False otherwise.

    """
    hashes = find_ledger_files()
    duplicates = {h: paths for h, paths in hashes.items() if len(paths) > 1}

    if duplicates:
        logging.warning(f"Found {len(duplicates)} groups of duplicate files")
        return True
    return True
