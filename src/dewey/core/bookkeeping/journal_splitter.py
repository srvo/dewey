#!/usr/bin/env python3

import os
from pathlib import Path
from dewey.core.base_script import BaseScript


class JournalSplitter(BaseScript):
    """
    Splits a journal file into separate files by year.
    """

    def __init__(self):
        super().__init__(config_section='bookkeeping')

    def split_journal_by_year(self, input_file: str, output_dir: str) -> None:
        """Split a journal file into separate files by year."""
        # Create output directory if it doesn't exist
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Get account number from filename
        account_num = os.path.basename(input_file).split("_")[1].split(".")[0]
        bank_account = f"assets:checking:mercury{account_num}"

        # Initialize files dict to store transactions by year
        files = {}
        current_year = None
        current_transaction = []

        with open(input_file) as f:
            for line in f:
                # Check if this is a new transaction (starts with a date)
                if line.strip() and line[0].isdigit():
                    # If we have a previous transaction, write it
                    if current_transaction and current_year:
                        if current_year not in files:
                            output_file = os.path.join(
                                output_dir,
                                f"{os.path.basename(input_file).replace('.journal', '')}_{current_year}.journal",
                            )
                            files[current_year] = open(output_file, "w")
                        files[current_year].write("".join(current_transaction))

                    # Start new transaction
                    current_transaction = [line]
                    try:
                        current_year = line.split("-")[0]
                    except:
                        current_year = None
                else:
                    # Continue current transaction
                    if line.strip():
                        # Replace generic accounts with proper ones
                        if "expenses:unknown" in line:
                            line = line.replace("expenses:unknown", "expenses:unclassified")
                        if "income:unknown" in line:
                            line = line.replace("income:unknown", bank_account)
                    current_transaction.append(line)

        # Write last transaction
        if current_transaction and current_year:
            if current_year not in files:
                output_file = os.path.join(
                    output_dir,
                    f"{os.path.basename(input_file).replace('.journal', '')}_{current_year}.journal",
                )
                files[current_year] = open(output_file, "w")
            files[current_year].write("".join(current_transaction))

        # Close all files
        for f in files.values():
            f.close()

    def run(self) -> None:
        """Process all journal files."""
        input_dir = "import/mercury/journal"
        output_dir = os.path.join(input_dir, "by_year")

        # Process each journal file
        for file in os.listdir(input_dir):
            if file.endswith(".journal") and not file.startswith("."):
                input_file = os.path.join(input_dir, file)
                self.split_journal_by_year(input_file, output_dir)


def main() -> None:
    """Main entrypoint for the script."""
    splitter = JournalSplitter()
    splitter.execute()


if __name__ == "__main__":
    main()