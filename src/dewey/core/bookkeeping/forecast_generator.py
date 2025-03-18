from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any
from dateutil.relativedelta import relativedelta
from dewey.utils import get_logger

ASSUMPTIONS = [
    "Asset acquired on 2023-12-01 for £25 (fair value £2500)",
    "Depreciation starts 2026-12-31 (operational date)",
    "30-year depreciation period (2026-2056)",
    "Monthly depreciation: £6.94 (£2500 / 30 years / 12 months)",
    "Revenue sharing terms: 50% of gross revenue until £125,975 recovered",
    "Revenue sharing terms: 1% of gross revenue until £234,000 recovered",
    "25% of gross revenue payable monthly to Mormair",
    "All amounts in GBP with comma-free formatting",
    "Entries append to existing journal file",
]


def validate_assumptions() -> None:
    """Validates key assumptions with user input."""
    logger = get_logger('forecast_generator')
    
    try:
        for i, assumption in enumerate(ASSUMPTIONS, 1):
            while True:
                response = input(f"{i}. {assumption} (y/n): ").strip().lower()
                if response == "y":
                    break
                if response == "n":
                    sys.exit()
                else:
                    pass
    except Exception as e:
        logger.exception(f"Error during assumption validation: {e!s}")
        sys.exit(1)


def create_acquisition_entry(acquisition_date: date) -> str:
    """Create the acquisition journal entry."""
    logger = get_logger('forecast_generator')
    
    try:
        entry = f"""{acquisition_date} Asset Acquisition
    assets:fixed:equipment:generator  £25.00
    equity:share-capital

; Fair value £2500
"""
        logger.debug("Created acquisition entry")
        return entry
    except Exception as e:
        logger.exception(f"Error creating acquisition entry: {e!s}")
        raise


def append_acquisition_entry(complete_ledger_file: str, acquisition_entry: str) -> None:
    """Append the acquisition entry to the complete ledger file."""
    logger = get_logger('forecast_generator')
    
    try:
        with open(complete_ledger_file, 'a') as f:
            f.write('\n' + acquisition_entry)
        logger.info(f"Appended acquisition entry to {complete_ledger_file}")
    except Exception as e:
        logger.exception(f"Error appending acquisition entry: {e!s}")
        raise


def initialize_forecast_ledger(forecast_ledger_file: str) -> None:
    """Initialize the forecast ledger file with header and assumptions."""
    logger = get_logger('forecast_generator')
    
    try:
        header = "; Generator Revenue and Depreciation Forecast\n\n"
        assumptions = "; Assumptions:\n" + "\n".join(f"; - {a}" for a in ASSUMPTIONS) + "\n\n"
        
        with open(forecast_ledger_file, 'w') as f:
            f.write(header + assumptions)
        logger.info(f"Initialized forecast ledger at {forecast_ledger_file}")
    except Exception as e:
        logger.exception(f"Error initializing forecast ledger: {e!s}")
        raise


def create_depreciation_entry(current_date: datetime) -> str:
    """Create the monthly depreciation entry."""
    logger = get_logger('forecast_generator')
    
    try:
        entry = f"""{current_date.strftime('%Y-%m-%d')} Monthly Generator Depreciation
    expenses:depreciation:equipment:generator  £6.94
    assets:fixed:equipment:generator:depreciation
"""
        logger.debug("Created depreciation entry")
        return entry
    except Exception as e:
        logger.exception(f"Error creating depreciation entry: {e!s}")
        raise


def create_revenue_entries(
    current_date: datetime,
    generator: dict,
) -> tuple[str, str, str]:
    """Create the monthly revenue, revenue share, and Mormair payment entries."""
    logger = get_logger('forecast_generator')
    
    try:
        # Calculate revenue share percentage based on total recovered
        if generator['recovered'] < 125975:
            share_pct = 0.50
        elif generator['recovered'] < 234000:
            share_pct = 0.01
        else:
            share_pct = 0
            
        # Calculate amounts
        revenue = 1000  # Placeholder monthly revenue
        share_amount = revenue * share_pct
        mormair_amount = revenue * 0.25
        
        # Create entries
        revenue_entry = f"""{current_date.strftime('%Y-%m-%d')} Monthly Generator Revenue
    assets:bank:business  £{revenue:.2f}
    income:generator
"""
        
        share_entry = f"""{current_date.strftime('%Y-%m-%d')} Revenue Share Payment
    expenses:revenue-share  £{share_amount:.2f}
    assets:bank:business
"""
        
        mormair_entry = f"""{current_date.strftime('%Y-%m-%d')} Mormair Payment
    expenses:services:mormair  £{mormair_amount:.2f}
    assets:bank:business
"""
        
        logger.debug("Created revenue entries")
        return revenue_entry, share_entry, mormair_entry
    except Exception as e:
        logger.exception(f"Error creating revenue entries: {e!s}")
        raise


def generate_journal_entries(
    complete_ledger_file: str,
    forecast_ledger_file: str,
) -> None:
    """Generate all journal entries for the forecast period."""
    logger = get_logger('forecast_generator')
    
    try:
        # Validate assumptions with user
        validate_assumptions()
        
        # Create acquisition entry
        acquisition_date = date(2023, 12, 1)
        acquisition_entry = create_acquisition_entry(acquisition_date)
        append_acquisition_entry(complete_ledger_file, acquisition_entry)
        
        # Initialize forecast ledger
        initialize_forecast_ledger(forecast_ledger_file)
        
        # Generate monthly entries from operational date
        start_date = datetime(2026, 12, 31)
        end_date = datetime(2056, 12, 31)
        current_date = start_date
        generator = {'recovered': 0}
        
        while current_date <= end_date:
            try:
                # Create entries
                depreciation_entry = create_depreciation_entry(current_date)
                revenue_entry, share_entry, mormair_entry = create_revenue_entries(
                    current_date, generator
                )
                
                # Write entries to forecast ledger
                with open(forecast_ledger_file, 'a') as f:
                    f.write('\n'.join([
                        depreciation_entry,
                        revenue_entry,
                        share_entry,
                        mormair_entry,
                        ''  # Empty line between months
                    ]))
                
                # Move to next month
                current_date += relativedelta(months=1)
                generator['recovered'] += 1000  # Update recovered amount
                
            except Exception as e:
                logger.error(f"Error processing month {current_date}: {e!s}")
                continue
        
        logger.info("Successfully generated all forecast entries")
        
    except Exception as e:
        logger.exception(f"Error generating journal entries: {e!s}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Generate forecast journal entries')
    parser.add_argument('complete_ledger', help='Path to complete ledger file')
    parser.add_argument('forecast_ledger', help='Path to forecast ledger file')
    args = parser.parse_args()

    # Set up logging
    log_dir = os.path.join(os.getenv('DEWEY_DIR', os.path.expanduser('~/dewey')), 'logs')
    logger = get_logger('forecast_generator', log_dir)
    
    generate_journal_entries(args.complete_ledger, args.forecast_ledger)


if __name__ == '__main__':
    main()
