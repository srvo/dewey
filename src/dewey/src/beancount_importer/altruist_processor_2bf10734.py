import re
import sys  # Import the sys module
from datetime import datetime

from dateutil.relativedelta import relativedelta


def process_altruist_income(journal_file):
    """Processes the journal file to recognize altruist income at the beginning of each quarter,
    recognize one month's worth of revenue as fee income, and create deferred revenue entries
    for the balance. Generates additional fee income entries at the beginning of each month
    in the quarter.
    """
    with open(journal_file) as f:
        journal_content = f.read()

    # Regex to find income transactions from altruist at the beginning of a quarter
    # This regex is a starting point and might need adjustments based on your specific journal format
    transaction_regex = re.compile(
        r"(\d{4}[/\-]\d{2}[/\-]\d{2})\s+(.*?Altruist.*?\n"  # Date and description containing "Altruist"
        r".*?\n"  # Match all lines until the postings
        r"(\s{2,}income:altruist\s+([0-9.,-]+).*?\n)",  # Capture income posting
        re.MULTILINE | re.DOTALL,
    )

    matches = transaction_regex.finditer(journal_content)

    output_transactions = []

    for match in matches:
        date_str = match.group(1)
        description = match.group(2).strip()
        match.group(3).strip()
        amount = float(match.group(4).replace(",", ""))  # Convert amount to float

        date_obj = datetime.strptime(
            date_str,
            "%Y-%m-%d" if "-" in date_str else "%Y/%m/%d",
        ).date()

        # Check if the date is the beginning of a quarter (Jan 1, Apr 1, Jul 1, Oct 1)
        if date_obj.month in [1, 4, 7, 10] and date_obj.day == 1:
            # Calculate one month's worth of revenue
            one_month_revenue = round(amount / 3, 2)

            # Create fee income transaction
            fee_income_transaction = f"""
{date_str} * Fee income from Altruist
    ; Original transaction: {description}
    income:fees    {one_month_revenue}
    assets:deferred_revenue   {-one_month_revenue}
"""
            output_transactions.append(fee_income_transaction)

            # Create deferred revenue entry for the remaining amount
            round(amount - one_month_revenue, 2)
            deferred_revenue_transaction = f"""
{date_str} * Deferred revenue from Altruist
    ; Original transaction: {description}
    assets:bank                      {-amount}
    assets:deferred_revenue         {amount}
"""
            output_transactions.append(deferred_revenue_transaction)

            # Generate fee income entries for the next two months
            for i in range(1, 3):
                next_month = date_obj + relativedelta(months=i)
                next_month_str = next_month.strftime("%Y-%m-%d")
                fee_income_transaction = f"""
{next_month_str} * Fee income from Altruist
    ; Original transaction: {description}
    assets:deferred_revenue   {-one_month_revenue}
    income:fees    {one_month_revenue}
"""
                output_transactions.append(fee_income_transaction)

    # Combine the original journal content with the new transactions
    return journal_content + "\n".join(output_transactions)


if __name__ == "__main__":
    if len(sys.argv) > 1:  # Check if a command-line argument is provided
        journal_file = sys.argv[1]  # Get the journal file from the command line
    else:
        sys.exit(1)  # Exit the script if no argument is provided
    output_content = process_altruist_income(journal_file)

    with open(journal_file, "w") as f:
        f.write(output_content)
