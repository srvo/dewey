#!/usr/bin/env python3
import os
import sys
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict
from dewey.utils import get_logger

class LedgerFormatChecker:
    def __init__(self, journal_file: str) -> None:
        self.journal_file = Path(journal_file)
        self.logger = get_logger('ledger_checker')
        self.warnings: List[str] = []
        self.errors: List[str] = []
        self.transactions: List[Dict] = []

    def check_file_exists(self) -> bool:
        """Check if the journal file exists."""
        if not self.journal_file.exists():
            self.errors.append(f"Journal file not found: {self.journal_file}")
            self.logger.error(f"Journal file not found: {self.journal_file}")
            return False
        return True

    def check_hledger_format(self) -> bool:
        """Check if the file can be parsed by hledger."""
        try:
            result = subprocess.run(
                ['hledger', '-f', str(self.journal_file), 'print'],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                self.errors.append(f"hledger format check failed: {result.stderr}")
                self.logger.error(f"hledger format check failed: {result.stderr}")
                return False
                
            self.logger.info("hledger format check passed")
            return True
            
        except subprocess.CalledProcessError as e:
            self.errors.append(f"Failed to run hledger: {str(e)}")
            self.logger.error(f"Failed to run hledger: {str(e)}")
            return False

    def check_balanced_transactions(self) -> bool:
        """Check if all transactions are balanced."""
        try:
            result = subprocess.run(
                ['hledger', '-f', str(self.journal_file), 'balance', '--check-balanced'],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                self.errors.append(f"Found unbalanced transactions: {result.stderr}")
                self.logger.error(f"Found unbalanced transactions: {result.stderr}")
                return False
                
            self.logger.info("All transactions are balanced")
            return True
            
        except subprocess.CalledProcessError as e:
            self.errors.append(f"Failed to check transaction balance: {str(e)}")
            self.logger.error(f"Failed to check transaction balance: {str(e)}")
            return False

    def run_all_checks(self) -> bool:
        """Run all ledger validation checks."""
        self.logger.info(f"Starting ledger validation for {self.journal_file}")
        
        checks = [
            self.check_file_exists,
            self.check_hledger_format,
            self.check_balanced_transactions
        ]
        
        success = True
        for check in checks:
            if not check():
                success = False
                
        if success:
            self.logger.info("All ledger checks passed successfully")
        else:
            if self.warnings:
                self.logger.warning("Validation warnings:")
                for warning in self.warnings:
                    self.logger.warning(f"- {warning}")
                    
            if self.errors:
                self.logger.error("Validation errors:")
                for error in self.errors:
                    self.logger.error(f"- {error}")
                    
        return success


def main():
    parser = argparse.ArgumentParser(description='Check ledger file format and validity')
    parser.add_argument('journal_file', help='Path to the journal file to check')
    args = parser.parse_args()

    # Set up logging
    log_dir = os.path.join(os.getenv('DEWEY_DIR', os.path.expanduser('~/dewey')), 'logs')
    logger = get_logger('ledger_checker', log_dir)
    
    checker = LedgerFormatChecker(args.journal_file)
    if not checker.run_all_checks():
        sys.exit(1)


if __name__ == '__main__':
    main()
