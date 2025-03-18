#!/usr/bin/env python3

import os
import sys
import re
import shutil
from typing import List, Dict, Optional
import argparse
from pathlib import Path
from dewey.utils import get_logger

# File header: Corrects formatting issues in Hledger journal files.

def parse_transactions(content: str) -> List[Dict]:
    """Parse all transactions from journal content.

    Args:
        content (str): The content of the journal file.

    Returns:
        List[Dict]: A list of dictionaries, where each dictionary represents a transaction.
    """
    logger = get_logger('journal_fixer')
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

    logger.debug(f"Parsed {len(transactions)} transactions")
    return transactions


def process_transactions(transactions: List[Dict]) -> str:
    """Process transactions and return fixed journal content.

    Args:
        transactions (List[Dict]): A list of transaction dictionaries.

    Returns:
        str: The fixed journal content as a string.
    """
    logger = get_logger('journal_fixer')
    fixed_entries = []

    for transaction in transactions:
        # Build the transaction entry
        entry = f"{transaction['date']} {transaction['description']}\n"
        for posting in transaction["postings"]:
            entry += f"    {posting['account']}  {posting['amount']}\n"
        fixed_entries.append(entry)

    logger.debug(f"Processed {len(transactions)} transactions")
    return "\n".join(fixed_entries)


def parse_transaction(lines: List[str]) -> Optional[Dict]:
    """Parse a transaction from a list of lines.

    Args:
        lines (List[str]): A list of strings representing the lines of a transaction.

    Returns:
        Optional[Dict]: A dictionary representing the transaction, or None if parsing fails.
    """
    logger = get_logger('journal_fixer')
    
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
        logging.error(f"File not found: {file_path}")
        return

    logging.info(f"Processing file: {file_path}")

    # Create backup first
    backup_path = file_path + ".bak"
    try:
        shutil.copy2(file_path, backup_path)

        # Read and process transactions
        with open(file_path) as f:
            content = f.read()

        transactions = parse_transactions(content)
        logging.debug(f"Processing {len(transactions)} transactions")

        # Rest of processing logic
        fixed_content = process_transactions(transactions)

        # Write corrected content
        with open(file_path, "w") as f:
            f.write(fixed_content)

    except Exception as e:
        logging.exception(f"Failed to process {file_path}")
        if os.path.exists(backup_path):
            logging.info(f"Restoring from backup: {backup_path}")
            shutil.move(backup_path, file_path)
        raise


def main() -> None:
    """Main function to process all journal files."""
    logging.info("Starting journal entries correction")

    # Process all journal files in the current directory
    for filename in os.listdir("."):
        if filename.endswith(".journal"):
            process_journal_file(filename)

    logging.info("Completed journal entries correction")


def fix_transaction(lines: List[str]) -> List[str]:
    """Fix common issues in a transaction."""
    logger = get_logger('journal_fixer')
    fixed_lines = []
    
    for line in lines:
        # Fix common account name issues
        line = (
            line.replace('expenses:unknown', 'expenses:unclassified')
               .replace('income:unknown', 'income:unclassified')
               .replace('assets:checking:unknown', 'assets:checking:main')
        )
        
        # Fix spacing issues
        if line.strip() and line.strip()[0].isdigit():
            # Date line should not be indented
            fixed_lines.append(line.lstrip())
        elif line.strip() and not line.startswith(';'):
            # Account postings should be indented with 4 spaces
            fixed_lines.append('    ' + line.lstrip())
        else:
            # Comments and empty lines preserved as is
            fixed_lines.append(line)
    
    return fixed_lines


def fix_journal(input_file: str, output_file: str = None) -> None:
    """Fix common issues in a journal file."""
    logger = get_logger('journal_fixer')
    
    try:
        input_path = Path(input_file)
        
        if not input_path.exists():
            logger.error(f"Input file does not exist: {input_path}")
            sys.exit(1)
        
        # If no output file specified, create one with '_fixed' suffix
        if output_file is None:
            output_file = str(input_path.with_suffix('')) + '_fixed.journal'
        output_path = Path(output_file)
        
        logger.info(f"Fixing journal file: {input_path}")
        logger.info(f"Output file: {output_path}")
        
        # Process file
        current_transaction = []
        fixed_transactions = []
        
        with open(input_path) as f:
            for line in f:
                # Start of new transaction
                if line.strip() and not line.startswith(' ') and not line.startswith(';'):
                    # Fix previous transaction if exists
                    if current_transaction:
                        fixed_transactions.extend(fix_transaction(current_transaction))
                        fixed_transactions.append('\n')  # Add blank line between transactions
                    
                    # Start new transaction
                    current_transaction = [line]
                else:
                    current_transaction.append(line)
        
        # Fix final transaction
        if current_transaction:
            fixed_transactions.extend(fix_transaction(current_transaction))
        
        # Write fixed journal
        with open(output_path, 'w') as f:
            f.writelines(fixed_transactions)
        
        logger.info("Journal fixing completed successfully")
        
    except Exception as e:
        logger.error(f"Error fixing journal: {str(e)}", exc_info=True)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Fix common issues in a journal file')
    parser.add_argument('input_file', help='Input journal file')
    parser.add_argument('--output-file', help='Output file (default: input_fixed.journal)')
    args = parser.parse_args()

    # Set up logging
    log_dir = os.path.join(os.getenv('DEWEY_DIR', os.path.expanduser('~/dewey')), 'logs')
    logger = get_logger('journal_fixer', log_dir)
    
    fix_journal(args.input_file, args.output_file)


if __name__ == "__main__":
    main()
