#!/usr/bin/env python3

import logging
import os
import re
import shutil
from typing import List, Dict, Optional

# File header: Corrects formatting issues in Hledger journal files.

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_transactions(content: str) -> List[Dict]:
    """Parse all transactions from journal content.

    Args:
        content (str): The content of the journal file.

    Returns:
        List[Dict]: A list of dictionaries, where each dictionary represents a transaction.
    """
    transactions = []
    current_transaction = []

    for line in content.split("\n"):
        if line.strip() == "":
            if current_transaction:
                transaction = parse_transaction(current_transaction)
                if transaction:
                    transactions.append(transaction)
                current_transaction = []
        else:
            current_transaction.append(line)

    if current_transaction:
        transaction = parse_transaction(current_transaction)
        if transaction:
            transactions.append(transaction)

    return transactions


def process_transactions(transactions: List[Dict]) -> str:
    """Process transactions and return fixed journal content.

    Args:
        transactions (List[Dict]): A list of transaction dictionaries.

    Returns:
        str: The fixed journal content as a string.
    """
    fixed_entries = []

    for transaction in transactions:
        # Build the transaction entry
        entry = f"{transaction['date']} {transaction['description']}\n"
        for posting in transaction["postings"]:
            entry += f"    {posting['account']}  {posting['amount']}\n"
        fixed_entries.append(entry)

    return "\n".join(fixed_entries)


def parse_transaction(lines: List[str]) -> Optional[Dict]:
    """Parse a transaction from a list of lines.

    Args:
        lines (List[str]): A list of strings representing the lines of a transaction.

    Returns:
        Optional[Dict]: A dictionary representing the transaction, or None if parsing fails.
    """
    if not lines or not lines[0].strip():
        logger.debug("Empty transaction lines encountered")
        return None

    # Parse transaction date and description
    first_line = lines[0].strip()
    date_match = re.match(r"(\d{4}-\d{2}-\d{2})", first_line)
    if not date_match:
        logger.debug("Invalid transaction date format: %s", first_line)
        return None

    transaction = {
        "date": date_match.group(1),
        "description": first_line[len(date_match.group(1)) :].strip(),
        "postings": [],
    }

    # Parse postings
    for line in lines[1:]:
        if line.strip():
            parts = line.strip().split()
            if len(parts) >= 2:
                account = parts[0]
                amount = parts[1] if len(parts) > 1 else None
                transaction["postings"].append(
                    {
                        "account": account,
                        "amount": amount,
                    },
                )

    return transaction


def process_journal_file(file_path: str) -> None:
    """Process a journal file and fix all transactions.

    Args:
        file_path (str): The path to the journal file.

    Raises:
        Exception: If the file processing fails, the original exception is re-raised after attempting to restore from backup.
    """
    if not os.path.exists(file_path):
        logger.error("File not found: %s", file_path)
        return

    logger.info("Processing file: %s", file_path)

    # Create backup first
    backup_path = file_path + ".bak"
    try:
        shutil.copy2(file_path, backup_path)

        # Read and process transactions
        with open(file_path) as f:
            content = f.read()

        transactions = parse_transactions(content)
        logger.debug("Processing %d transactions", len(transactions))

        # Rest of processing logic
        fixed_content = process_transactions(transactions)

        # Write corrected content
        with open(file_path, "w") as f:
            f.write(fixed_content)

    except Exception as e:
        logger.exception("Failed to process %s", file_path)
        if os.path.exists(backup_path):
            logger.info("Restoring from backup: %s", backup_path)
            shutil.move(backup_path, file_path)
        raise


def main() -> None:
    """Main function to process all journal files."""
    logger.info("Starting journal entries correction")

    # Process all journal files in the current directory
    for filename in os.listdir("."):
        if filename.endswith(".journal"):
            process_journal_file(filename)

    logger.info("Completed journal entries correction")


if __name__ == "__main__":
    main()
