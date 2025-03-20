#!/usr/bin/env python3

import os
import re
import shutil
from typing import List, Dict, Optional

from dewey.core.base_script import BaseScript


class JournalFixer(BaseScript):
    """Corrects formatting issues in Hledger journal files."""

    def __init__(self) -> None:
        """Initializes the JournalFixer with bookkeeping config."""
        super().__init__(config_section='bookkeeping')

    def parse_transactions(self, content: str) -> List[Dict]:
        """Parse all transactions from journal content.

        Args:
            content: The content of the journal file.

        Returns:
            A list of dictionaries, where each dictionary represents a transaction.
        """
        transactions = []
        current_transaction = []

        for line in content.split("\n"):
            if line.strip() == "":
                if current_transaction:
                    transaction = self.parse_transaction(current_transaction)
                    if transaction:
                        transactions.append(transaction)
                    current_transaction = []
            else:
                current_transaction.append(line)

        if current_transaction:
            transaction = self.parse_transaction(current_transaction)
            if transaction:
                transactions.append(transaction)

        return transactions

    def process_transactions(self, transactions: List[Dict]) -> str:
        """Process transactions and return fixed journal content.

        Args:
            transactions: A list of transaction dictionaries.

        Returns:
            The fixed journal content as a string.
        """
        fixed_entries = []

        for transaction in transactions:
            # Build the transaction entry
            entry = f"{transaction['date']} {transaction['description']}\n"
            for posting in transaction["postings"]:
                entry += f"    {posting['account']}  {posting['amount']}\n"
            fixed_entries.append(entry)

        return "\n".join(fixed_entries)

    def parse_transaction(self, lines: List[str]) -> Optional[Dict]:
        """Parse a transaction from a list of lines.

        Args:
            lines: A list of strings representing the lines of a transaction.

        Returns:
            A dictionary representing the transaction, or None if parsing fails.
        """
        if not lines or not lines[0].strip():
            self.logger.debug("Empty transaction lines encountered")
            return None

        # Parse transaction date and description
        first_line = lines[0].strip()
        date_match = re.match(r"(\d{4}-\d{2}-\d{2})", first_line)
        if not date_match:
            self.logger.debug("Invalid transaction date format: %s", first_line)
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

    def process_journal_file(self, file_path: str) -> None:
        """Process a journal file and fix all transactions.

        Args:
            file_path: The path to the journal file.

        Raises:
            Exception: If the file processing fails, the original exception is re-raised after attempting to restore from backup.
        """
        if not os.path.exists(file_path):
            self.logger.error(f"File not found: {file_path}")
            return

        self.logger.info(f"Processing file: {file_path}")

        # Create backup first
        backup_path = file_path + ".bak"
        try:
            shutil.copy2(file_path, backup_path)

            # Read and process transactions
            with open(file_path) as f:
                content = f.read()

            transactions = self.parse_transactions(content)
            self.logger.debug(f"Processing {len(transactions)} transactions")

            # Rest of processing logic
            fixed_content = self.process_transactions(transactions)

            # Write corrected content
            with open(file_path, "w") as f:
                f.write(fixed_content)

        except Exception as e:
            self.logger.exception(f"Failed to process {file_path}")
            if os.path.exists(backup_path):
                self.logger.info(f"Restoring from backup: {backup_path}")
                shutil.move(backup_path, file_path)
            raise

    def run(self) -> None:
        """Main function to process all journal files."""
        self.logger.info("Starting journal entries correction")

        # Process all journal files in the current directory
        for filename in os.listdir("."):
            if filename.endswith(".journal"):
                self.process_journal_file(filename)

        self.logger.info("Completed journal entries correction")


def main() -> None:
    """Main function to process all journal files."""
    fixer = JournalFixer()
    fixer.execute()


if __name__ == "__main__":
    main()
