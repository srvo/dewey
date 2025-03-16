#!/usr/bin/env python3
import fnmatch
import json
import re
import shutil
from pathlib import Path
from typing import List, Tuple, Dict, Any

from dewey.config import logging  # Centralized logging

logger = logging.getLogger(__name__)

# File header: Automatically categorizes transactions based on predefined rules.

# Rule sources in priority order (lower numbers = higher priority)
RULE_SOURCES = [
    ("overrides.json", 0),  # Highest priority
    ("manual_rules.json", 1),
    ("base_rules.json", 2),  # Lowest priority
]

# TODO: Fix search/replace block
]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Use absolute path for classification rules file
CLASSIFICATION_FILE = Path.home() / "books/import/mercury/classification_rules.json"
LEDGER_FILE = Path.home() / ".hledger.journal"
BACKUP_EXT = ".bak"


def load_classification_rules() -> Dict:
    """Load classification rules from JSON files."""
    logger.info("Loading classification rules")
    return {}  # Placeholder


def process_transactions(transactions: List[Dict], rules: Dict) -> List[Dict]:
    """Process transactions and categorize them based on rules."""
    logger.info("Processing transactions")
    return transactions  # Placeholder










def parse_journal_entries(file_path: Path) -> List[Dict]:
    """Parse hledger journal file into structured transactions.

    Args:
    ----
        file_path: The path to the hledger journal file.

    Returns:
    -------
        A list of structured transactions.

    """
    logger.info(f"Parsing journal file: {file_path}")

    with open(file_path) as f:
        content = f.read()

    transactions = []
    current_tx = {"postings": []}

    for line in content.split("\n"):
        line = line.rstrip()
        if not line:
            if current_tx.get("postings"):
                transactions.append(current_tx)
                current_tx = {"postings": []}
            continue

        if not current_tx.get("date"):
            # Transaction header line
            date_match = re.match(r"^(\d{4}-\d{2}-\d{2})(\s+.*?)$", line)
            if date_match:
                current_tx["date"] = date_match.group(1)
                current_tx["description"] = date_match.group(2).strip()
            continue

        # Parse posting lines
        if line.startswith("    "):
            parts = re.split(r"\s{2,}", line.strip(), 1)
            account = parts[0].strip()
            amount = parts[1].strip() if len(parts) > 1 else ""
            current_tx["postings"].append({"account": account, "amount": amount})

    if current_tx.get("postings"):
        transactions.append(current_tx)

    logger.info(f"Found {len(transactions)} transactions")
    return transactions




def serialize_transactions(transactions: List[Dict]) -> str:
    """Convert structured transactions back to journal format.

    Args:
    ----
        transactions: A list of structured transactions.

    Returns:
    -------
        A string representation of the transactions in journal format.

    """
    journal_lines = []

    for tx in transactions:
        header = f"{tx['date']} {tx['description']}"
        journal_lines.append(header)

        for posting in tx["postings"]:
            line = f"    {posting['account']}"
            if posting["amount"]:
                line += f"  {posting['amount']}"
            journal_lines.append(line)

        journal_lines.append("")  # Empty line between transactions

    return "\n".join(journal_lines).strip() + "\n"


def write_journal_file(content: str, file_path: Path) -> None:
    """Write updated journal file with backup.

    Args:
    ----
        content: The content to write to the journal file.
        file_path: The path to the journal file.

    """
    backup_path = file_path.with_suffix(f".{BACKUP_EXT}")

    try:
        # Create backup
        logger.info(f"Creating backup at {backup_path}")
        shutil.copy2(file_path, backup_path)

        # Write new content
        logger.info(f"Writing updated journal to {file_path}")
        with open(file_path, "w") as f:
            f.write(content)

    except Exception as e:
        logger.exception(f"Failed to write journal file: {e!s}")
        if backup_path.exists():
            logger.info("Restoring from backup")
            shutil.move(backup_path, file_path)
        raise


def main() -> None:
    """Main processing workflow."""
    try:
        # Load configuration
        rules = load_classification_rules()

        # Process journal entries
        transactions = parse_journal_entries(LEDGER_FILE)
        updated_transactions = process_transactions(transactions, rules)
        new_content = serialize_transactions(updated_transactions)

        # Write results
        write_journal_file(new_content, LEDGER_FILE)
        logger.info("Successfully updated journal entries")

    except Exception as e:
        logger.exception(f"Failed to process journal: {e!s}")
        raise


if __name__ == "__main__":
    main()
