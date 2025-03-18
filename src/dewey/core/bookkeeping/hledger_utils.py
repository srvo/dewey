#!/usr/bin/env python3

import re
import sys
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from dewey.utils import get_logger

class HledgerError(Exception):
    """Exception for hledger command failures."""


def get_balance(account: str, date: str) -> Optional[str]:
    """Get the balance for a specific account at a given date."""
    logger = get_logger('hledger_utils')
    
    try:
        logger.debug(f"Checking balance for account '{account}' at date {date}")
        
        cmd = [
            "hledger",
            "-f", "all.journal",
            "bal",
            account,
            "-e", date,
            "--depth", "1"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            logger.error(f"Balance check failed for '{account}': {result.stderr}")
            raise HledgerError(f"Balance check failed: {result.stderr}")

        # Extract the balance amount from the output
        lines = result.stdout.strip().split("\n")
        if lines:
            # The balance should be in the last line
            match = re.search(r"\$([0-9,.()-]+)", lines[-1])
            if match:
                balance = match.group(0)
                logger.debug(f"Balance for '{account}': {balance}")
                return balance
                
        logger.warning(f"No balance found for '{account}'")
        return None
        
    except subprocess.CalledProcessError as e:
        logger.exception(f"hledger command failed: {str(e)}")
        raise HledgerError(f"hledger command failed: {str(e)}")
    except Exception as e:
        logger.exception(f"Error getting balance for '{account}': {str(e)}")
        raise HledgerError(f"Error getting balance: {str(e)}")


def update_opening_balances(year: int) -> None:
    """Update opening balances for the specified year."""
    logger = get_logger('hledger_utils')
    
    try:
        # Get list of accounts
        cmd = [
            "hledger",
            "-f", "all.journal",
            "accounts"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        accounts = result.stdout.strip().split("\n")
        logger.info(f"Found {len(accounts)} accounts to process")
        
        # Get balances for each account
        opening_entries = []
        start_date = f"{year}-01-01"
        
        for account in accounts:
            balance = get_balance(account, start_date)
            if balance and balance != "$0.00":
                entry = f"""
{start_date} Opening Balance
    {account}    {balance}
    Equity:OpeningBalances
""".strip()
                opening_entries.append(entry)
                logger.debug(f"Added opening balance for '{account}': {balance}")
        
        # Write opening balances file
        output_file = Path(f"{year}_opening_balances.journal")
        with open(output_file, "w") as f:
            f.write("\n\n".join(opening_entries))
            
        logger.info(f"Wrote {len(opening_entries)} opening balances to {output_file}")
        
    except Exception as e:
        logger.exception(f"Failed to update opening balances: {str(e)}")
        raise HledgerError(f"Failed to update opening balances: {str(e)}")


def main() -> None:
    """Main entry point for hledger utilities."""
    logger = get_logger('hledger_utils')
    
    parser = argparse.ArgumentParser(description="Hledger utility functions")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Balance command
    balance_parser = subparsers.add_parser("balance", help="Get account balance")
    balance_parser.add_argument("account", help="Account to check")
    balance_parser.add_argument("date", help="Date to check balance at")
    
    # Opening balances command
    opening_parser = subparsers.add_parser("opening", help="Update opening balances")
    opening_parser.add_argument("year", type=int, help="Year to generate opening balances for")
    
    args = parser.parse_args()
    
    try:
        if args.command == "balance":
            balance = get_balance(args.account, args.date)
            if balance:
                print(f"Balance for {args.account} at {args.date}: {balance}")
            else:
                print(f"No balance found for {args.account}")
                
        elif args.command == "opening":
            update_opening_balances(args.year)
            
        else:
            parser.print_help()
            
    except HledgerError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
