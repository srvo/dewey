import os
import re
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from dateutil.relativedelta import relativedelta

from dewey.utils import get_logger

class DeferredRevenueError(Exception):
    """Exception for deferred revenue processing failures."""


def _parse_altruist_transactions(journal_content: str) -> List[re.Match]:
    """Parses the journal content to find Altruist income transactions."""
    logger = get_logger('deferred_revenue')
    
    try:
        transaction_regex = re.compile(
            r"(\d{4}-\d{2}-\d{2})\s+"  # Date (YYYY-MM-DD)
            r"(.*?altruist.*?)\n"  # Description with altruist (case insensitive)
            r"\s+Income:[^\s]+\s+([0-9.-]+)",  # Income posting with amount
            re.MULTILINE | re.IGNORECASE,
        )
        matches = list(transaction_regex.finditer(journal_content))
        logger.debug(f"Found {len(matches)} Altruist transactions")
        return matches
    except Exception as e:
        logger.exception(f"Failed to parse Altruist transactions: {str(e)}")
        raise DeferredRevenueError(f"Failed to parse Altruist transactions: {str(e)}")


def _generate_deferred_revenue_transactions(match: re.Match) -> List[str]:
    """Generates deferred revenue and fee income transactions."""
    logger = get_logger('deferred_revenue')
    
    try:
        date = datetime.strptime(match.group(1), "%Y-%m-%d")
        description = match.group(2).strip()
        amount = float(match.group(3))
        
        # Calculate monthly fee amount (total divided by 12)
        monthly_fee = round(amount / 12, 2)
        
        # Generate transactions
        transactions = []
        
        # Initial deferred revenue entry
        transactions.append(f"""
{date.strftime('%Y-%m-%d')} {description} - Initial Deferred Revenue
    Liabilities:DeferredRevenue  {amount}
    Income:Fees:Investment       -{amount}
""".strip())
        
        # Monthly recognition entries
        for i in range(12):
            recognition_date = date + relativedelta(months=i)
            transactions.append(f"""
{recognition_date.strftime('%Y-%m-%d')} {description} - Monthly Fee Recognition
    Income:Fees:Investment       {monthly_fee}
    Liabilities:DeferredRevenue  -{monthly_fee}
""".strip())
        
        logger.debug(f"Generated {len(transactions)} transactions for {description}")
        return transactions
        
    except Exception as e:
        logger.exception(f"Failed to generate deferred revenue transactions: {str(e)}")
        raise DeferredRevenueError(f"Failed to generate deferred revenue transactions: {str(e)}")


def process_altruist_income(journal_file: Path) -> Optional[str]:
    """Process Altruist income entries and generate deferred revenue transactions."""
    logger = get_logger('deferred_revenue')
    
    try:
        # Read journal file
        with open(journal_file) as f:
            content = f.read()
            
        # Parse transactions
        matches = _parse_altruist_transactions(content)
        if not matches:
            logger.info("No Altruist transactions found")
            return None
            
        # Generate deferred revenue transactions
        all_transactions = []
        for match in matches:
            transactions = _generate_deferred_revenue_transactions(match)
            all_transactions.extend(transactions)
            
        # Format output
        output = "\n\n".join(all_transactions)
        logger.info(f"Generated {len(all_transactions)} deferred revenue transactions")
        return output
        
    except Exception as e:
        logger.exception(f"Failed to process Altruist income: {str(e)}")
        raise DeferredRevenueError(f"Failed to process Altruist income: {str(e)}")


def main() -> None:
    """Main entry point for deferred revenue processing."""
    logger = get_logger('deferred_revenue')
    
    parser = argparse.ArgumentParser(description="Process Altruist income for deferred revenue")
    parser.add_argument("journal_file", type=Path, help="Path to the journal file")
    parser.add_argument("--output", type=Path, help="Path for the output file (optional)")
    args = parser.parse_args()
    
    try:
        # Process journal file
        output = process_altruist_income(args.journal_file)
        if not output:
            logger.info("No transactions to process")
            return
            
        # Write output
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            logger.info(f"Wrote deferred revenue transactions to {args.output}")
        else:
            print(output)
            
    except DeferredRevenueError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
import pytest
from pathlib import Path
from datetime import datetime
from dateutil.relativedelta import relativedelta
from src.dewey.core.bookkeeping.deferred_revenue import (
    _parse_altruist_transactions,
    _generate_deferred_revenue_transactions,
    process_altruist_income,
    DeferredRevenueError,
)

@pytest.fixture
def temp_journal(tmp_path):
    """Create a temporary journal file with sample content."""
    journal_path = tmp_path / "test.journal"
    content = """
    2023-01-01 Altruist Donation
        Income:Altruist  1000.00

    2023-02-15 Another Altruist Entry
        Income:Donations  500.00
    """
    journal_path.write_text(content)
    return journal_path

def test_parse_altruist_transactions_valid(temp_journal):
    with open(temp_journal) as f:
        content = f.read()
    matches = _parse_altruist_transactions(content)
    assert len(matches) == 2
    assert matches[0].group(1) == "2023-01-01"
    assert matches[0].group(3) == "1000.00"
    assert matches[1].group(1) == "2023-02-15"
    assert matches[1].group(3) == "500.00"

def test_parse_altruist_transactions_no_matches(tmp_path):
    empty_file = tmp_path / "empty.journal"
    empty_file.write_text("No altruist transactions here")
    with open(empty_file) as f:
        content = f.read()
    matches = _parse_altruist_transactions(content)
    assert len(matches) == 0

def test_parse_altruist_transactions_invalid_date(tmp_path):
    invalid_file = tmp_path / "invalid.journal"
    invalid_file.write_text("2023-13-01 Invalid Date  100.00")
    with open(invalid_file) as f:
        content = f.read()
    with pytest.raises(DeferredRevenueError):
        _parse_altruist_transactions(content)

def test_generate_deferred_transactions_valid():
    test_content = """
    2023-01-01 Altruist Test
        Income:Test  1200.00
    """
    matches = _parse_altruist_transactions(test_content)
    match = matches[0]
    transactions = _generate_deferred_revenue_transactions(match)
    assert len(transactions) == 13
    initial = transactions[0]
    assert "Liabilities:DeferredRevenue  1200.00" in initial
    assert "Income:Fees:Investment       -1200.00" in initial

    monthly = transactions[1]
    assert "2023-01-01" in monthly
    assert "Income:Fees:Investment       100.00" in monthly

def test_generate_deferred_transactions_edge_amount():
    test_content = """
    2023-01-01 Edge Case
        Income:Edge  12.01
    """
    matches = _parse_altruist_transactions(test_content)
    match = matches[0]
    transactions = _generate_deferred_revenue_transactions(match)
    monthly_fee = 12.01 / 12
    rounded = round(monthly_fee, 2)
    assert rounded == 1.00
    for t in transactions[1:]:
        assert f" {rounded} " in t

def test_generate_deferred_transactions_negative_amount(tmp_path):
    invalid_content = """
    2023-01-01 Negative
        Income:Test  -500.00
    """
    matches = _parse_altruist_transactions(invalid_content)
    match = matches[0]
    with pytest.raises(DeferredRevenueError):
        _generate_deferred_revenue_transactions(match)

def test_process_altruist_income_valid(temp_journal):
    output = process_altruist_income(temp_journal)
    assert output is not None
    assert len(output.split("\n\n")) == 2 * 13

def test_process_altruist_income_no_transactions(tmp_path):
    empty_file = tmp_path / "empty.journal"
    empty_file.write_text("No altruist entries")
    result = process_altruist_income(empty_file)
    assert result is None

def test_process_altruist_income_file_not_found(tmp_path):
    non_existent = tmp_path / "doesntexist.journal"
    with pytest.raises(DeferredRevenueError):
        process_altruist_income(non_existent)

def test_main_integration(tmp_path, monkeypatch):
    input_file = tmp_path / "input.journal"
    input_file.write_text("""
    2023-03-01 Test Entry
        Income:Test  1200.00
    """)
    output_file = tmp_path / "output.txt"

    monkeypatch.setattr("sys.argv", [
        "script_name",
        str(input_file),
        "--output",
        str(output_file),
    ])

    with pytest.raises(SystemExit) as exit_info:
        main()

    assert exit_info.value.code == 0
    assert output_file.exists()
    with open(output_file) as f:
        output_content = f.read()
    assert "2023-03-01 Test Entry" in output_content
    assert "Liabilities:DeferredRevenue  1200.00" in output_content

def test_main_error_handling(tmp_path, monkeypatch, capsys):
    invalid_file = tmp_path / "invalid.journal"
    invalid_file.write_text("Invalid content")

    monkeypatch.setattr("sys.argv", [
        "script_name",
        str(invalid_file),
    ])

    with pytest.raises(SystemExit) as exit_info:
        main()

    assert exit_info.value.code == 1
    captured = capsys.readouterr()
    assert "Failed to process Altruist income" in captured.err
