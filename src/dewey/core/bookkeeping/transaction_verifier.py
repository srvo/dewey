#!/usr/bin/env python3
import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import Any, List, Dict
from decimal import Decimal
from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import confirm
from dewey.utils import get_logger
from dotenv import find_dotenv, load_dotenv
from src.dewey.core.bookkeeping.classification_engine import ClassificationEngine, ClassificationError
from src.dewey.llm.api_clients.deepinfra import classify_errors

# Load environment variables from nearest .env file
# File header: Verifies transaction classifications and allows for correction via user feedback.
load_dotenv(find_dotenv())

# Check required environment variables
deepinfra_api_key = os.getenv("DEEPINFRA_API_KEY")
model_name = os.getenv("DEEPINFRA_DEFAULT_MODEL")

if not deepinfra_api_key:
    print("DEEPINFRA_API_KEY environment variable not set.")
    sys.exit(1)
if not model_name:
    print("DEEPINFRA_DEFAULT_MODEL environment variable not set.")
    sys.exit(1)


class ClassificationVerifier:
    def __init__(self, rules_path: Path, journal_path: Path) -> None:
        self.engine = ClassificationEngine(rules_path)
        self.writer = JournalWriter(journal_path.parent)
        self.journal_path = journal_path
        self.processed_feedback = 0
        self.logger = get_logger('transaction_verifier')

    @property
    def valid_categories(self) -> list[str]:
        """Get valid classification categories from engine."""
        return self.engine.categories

    def get_ai_suggestion(self, description: str) -> str:
        """Get AI classification suggestion using DeepInfra."""
        try:
            response = classify_errors(
                [f"Classify transaction: '{description}'"],
                instructions="Return ONLY the account path as category1:category2",
            )
            return response[0]["category"] if response else ""
        except Exception as e:
            self.logger.exception("AI classification failed: %s", str(e))
            return ""

    def get_transaction_samples(self, limit: int = 50) -> list[dict]:
        """Get sample transactions using hledger + DuckDB."""
        try:
            # Get CSV data directly from hledger
            cmd = [
                "hledger",
                "-f",
                str(self.journal_path),
                "print",
                "-O",
                "csv",
                "date:lastmonth",
                "not:unknown",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            if result.returncode != 0:
                self.logger.error("hledger export failed: %s", result.stderr)
                return []

            # Connect to in-memory DuckDB database
            import duckdb

            with duckdb.connect(":memory:") as con:
                # Create temp table from CSV data
                con.execute(
                    """
                    CREATE TEMP TABLE txns AS
                    SELECT * FROM 'csv:stdin' (header=true)
                    WHERE date BETWEEN
                        DATE_TRUNC('month', CURRENT_DATE - INTERVAL 1 MONTH) AND
                        DATE_TRUNC('month', CURRENT_DATE) - INTERVAL 1 DAY
                """,
                    [result.stdout],
                )

                # Query with proper typing and ordering
                query = f"""
                    SELECT
                        date,
                        description,
                        amount,
                        account,
                        STRFTIME(STRPTIME(date, '%Y-%m-%d'), '%Y-%m-%d') AS parsed_date
                    FROM txns
                    ORDER BY parsed_date DESC
                    LIMIT {limit}
                """
                result = con.execute(query).fetchall()
                columns = [col[0] for col in con.description]

                return [dict(zip(columns, row, strict=False)) for row in result]

        except Exception as e:
            self.logger.exception("DuckDB processing failed: %s", str(e))
            return []

    def prompt_for_feedback(self, tx: dict) -> None:
        """Interactive prompt for transaction verification."""
        if not isinstance(tx, dict):
            self.logger.error("Invalid transaction format - expected dict, got %s", type(tx))
            return

        try:
            desc = tx.get("description", "Unknown transaction")
            account = tx.get("account", "UNCLASSIFIED")
            amount_str = tx.get("amount", "0")
            "".join(
                [c for c in amount_str.split()[-1] if c in "0123456789-."],
            ) or "0.00"

            # Get AI suggestion
            suggested_category = self.get_ai_suggestion(desc)
            if suggested_category:
                pass

            response = confirm("Is this classification correct?", default=True)

            if not response:
                default = suggested_category if suggested_category else ""
                new_category = prompt(
                    "Enter correct account path: ",
                    default=default,
                ).strip()

                if new_category:
                    feedback = f"Classify '{desc}' as {new_category}"
                    try:
                        self.engine.process_feedback(feedback, self.writer)
                        self.processed_feedback += 1
                        self.logger.info(
                            "Updated classification: %s → %s",
                            account,
                            new_category,
                        )
                    except ClassificationError as e:
                        self.logger.exception("Invalid category: %s", str(e))
        except Exception as e:
            self.logger.exception("Error processing transaction: %s", str(e))
            self.logger.debug("Problematic transaction data: %s", tx)

    def generate_report(self, total: int) -> None:
        """Generate verification session summary."""
        if self.processed_feedback > 0:
            pass

    def main(self) -> None:
        """Interactive verification workflow."""
        samples = self.get_transaction_samples()

        if not samples:
            self.logger.error("No transactions found for verification")
            return

        for _idx, tx in enumerate(samples, 1):
            self.prompt_for_feedback(tx)

        self.generate_report(len(samples))


def parse_transaction(lines: List[str]) -> Dict[str, Any]:
    """Parse a transaction from journal lines."""
    logger = get_logger('transaction_verifier')
    
    transaction = {
        'date': None,
        'description': None,
        'postings': [],
        'total': Decimal('0')
    }
    
    # Parse first line for date and description
    if lines and lines[0].strip():
        parts = lines[0].strip().split(maxsplit=1)
        if len(parts) >= 1:
            transaction['date'] = parts[0]
        if len(parts) >= 2:
            transaction['description'] = parts[1]
    
    # Parse postings
    for line in lines[1:]:
        if line.strip() and line.startswith(' '):
            parts = line.strip().split()
            if len(parts) >= 2:
                account = parts[0]
                amount = Decimal(parts[-1].replace('$', ''))
                transaction['postings'].append({
                    'account': account,
                    'amount': amount
                })
                transaction['total'] += amount
    
    return transaction


def verify_transactions(input_file: str) -> None:
    """Verify transactions in a journal file."""
    logger = get_logger('transaction_verifier')
    
    try:
        input_path = Path(input_file)
        
        if not input_path.exists():
            logger.error(f"Input file does not exist: {input_path}")
            sys.exit(1)
        
        logger.info(f"Verifying transactions in: {input_path}")
        
        # Read and verify transactions
        current_transaction = []
        line_number = 0
        error_count = 0
        
        with open(input_path) as f:
            for line in f:
                line_number += 1
                
                # Start of new transaction
                if line.strip() and not line.startswith(' ') and not line.startswith(';'):
                    # Verify previous transaction if exists
                    if current_transaction:
                        transaction = parse_transaction(current_transaction)
                        
                        # Check if transaction balances
                        if abs(transaction['total']) > Decimal('0.001'):
                            logger.error(
                                f"Transaction does not balance at line {line_number - len(current_transaction)}:",
                                extra={
                                    'date': transaction['date'],
                                    'description': transaction['description'],
                                    'total': float(transaction['total'])
                                }
                            )
                            error_count += 1
                    
                    # Start new transaction
                    current_transaction = [line]
                else:
                    current_transaction.append(line)
        
        # Verify final transaction
        if current_transaction:
            transaction = parse_transaction(current_transaction)
            if abs(transaction['total']) > Decimal('0.001'):
                logger.error(
                    f"Transaction does not balance at line {line_number - len(current_transaction)}:",
                    extra={
                        'date': transaction['date'],
                        'description': transaction['description'],
                        'total': float(transaction['total'])
                    }
                )
                error_count += 1
        
        # Report results
        if error_count == 0:
            logger.info("All transactions verified successfully")
        else:
            logger.error(f"Found {error_count} unbalanced transactions")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"Error verifying transactions: {str(e)}", exc_info=True)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Verify transactions in a journal file')
    parser.add_argument('input_file', help='Input journal file')
    args = parser.parse_args()

    # Set up logging
    log_dir = os.path.join(os.getenv('DEWEY_DIR', os.path.expanduser('~/dewey')), 'logs')
    logger = get_logger('transaction_verifier', log_dir)
    
    verify_transactions(args.input_file)


if __name__ == '__main__':
    main()
