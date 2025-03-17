import logging
import os
import re
import sys
from datetime import datetime
# File header: Processes Altruist income for deferred revenue recognition.

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

from dateutil.relativedelta import relativedelta
from typing import List
import re

def _parse_altruist_transactions(journal_content: str) -> List[re.Match]:
    """Parses the journal content to find Altruist income transactions.

    Args:
    ----
        journal_content: The content of the journal file as a string.

    Returns:
    -------
        A list of match objects, each representing an Altruist income transaction.

    """
    transaction_regex = re.compile(
        r"(\d{4}-\d{2}-\d{2})\s+"  # Date (YYYY-MM-DD)
        r"(.*?altruist.*?)\n"  # Description with altruist (case insensitive)
        r"\s+Income:[^\s]+\s+([0-9.-]+)",  # Income posting with amount
        re.MULTILINE | re.IGNORECASE,
    )
    return list(transaction_regex.finditer(journal_content)) # type: ignore


def _generate_deferred_revenue_transactions(match: re.Match) -> List[str]:
    """Generates deferred revenue and fee income transactions for a given Altruist transaction.

    Args:
    ----
        match: A match object representing an Altruist income transaction.

    Returns:
    -------
        A list of transaction strings to be added to the journal.

    """
    date_str = match.group(1)
    description = match.group(2).strip()
    amount = float(match.group(3))
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    one_month_revenue = round(amount / 3, 2)

    transactions = []

    # Create initial fee income transaction
    fee_income_transaction = f"""
{date_str} * Fee income from Altruist
    ; Original transaction: {description}
    income:fees    {one_month_revenue}
    assets:deferred_revenue   {-one_month_revenue}"""
    transactions.append(fee_income_transaction)

    # Create deferred revenue entry
    deferred_revenue_transaction = f"""
{date_str} * Deferred revenue from Altruist
    ; Original transaction: {description}
    assets:bank                      {-amount}
    assets:deferred_revenue         {amount}"""
    transactions.append(deferred_revenue_transaction)

    # Generate fee income entries for the next two months
    for month in range(1, 3):
        next_month = date_obj + relativedelta(months=month)
        next_month_str = next_month.strftime("%Y-%m-%d")
        fee_income_transaction = f"""
{next_month_str} * Fee income from Altruist
    ; Original transaction: {description}
    assets:deferred_revenue   {-one_month_revenue}
    income:fees    {one_month_revenue}"""
        transactions.append(fee_income_transaction)

    return transactions


def process_altruist_income(journal_file: str) -> str:
    """Processes the journal file to recognize altruist income.

    Recognizes altruist income at the beginning of each quarter,
    recognizes one month's worth of revenue as fee income, and creates deferred revenue entries
    for the balance. Generates additional fee income entries at the beginning of each month
    in the quarter.

    Args:
    ----
        journal_file: The path to the journal file.

    Returns:
    -------
        The updated content of the journal file with the new transactions.

    Raises:
    ------
        FileNotFoundError: If the journal file does not exist.

    """
    if not os.path.exists(journal_file):
        logger.error(f"Could not find journal file at: {journal_file}")
        msg = f"Could not find journal file at: {journal_file}"
        raise FileNotFoundError(msg)

    with open(journal_file) as f:
        journal_content = f.read()

    matches = _parse_altruist_transactions(journal_content)

    if not matches:
        logger.info("No Altruist transactions found in %s", journal_file)
        return journal_content

    output_transactions = []

    for match in matches:
        try:
            transactions = _generate_deferred_revenue_transactions(match)
            output_transactions.extend(transactions)
        except Exception as e:
            logger.exception(
                "Failed to generate transactions for match: %s", match.group(0)
            )
            continue

    if output_transactions:
        output_content = journal_content + "\n" + "\n".join(output_transactions) + "\n"
        logger.info(
            "Successfully processed %d Altruist transactions in %s",
            len(matches),
            journal_file,
        )
    else:
        output_content = journal_content
        logger.info("No new transactions added to %s", journal_file)

    return output_content


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(1)

    journal_file = os.path.abspath(sys.argv[1])

    try:
        output_content = process_altruist_income(journal_file)

        backup_file = journal_file + ".bak"
        with open(journal_file) as src, open(backup_file, "w") as dst:
            dst.write(src.read())

        with open(journal_file, "w") as f:
            f.write(output_content)
        logger.info("Journal file updated successfully: %s", journal_file)

    except FileNotFoundError:
        logger.error("Journal file not found: %s", journal_file)
        sys.exit(1)
    except Exception as e:
        logger.exception("An unexpected error occurred: %s", str(e))
        sys.exit(1)
