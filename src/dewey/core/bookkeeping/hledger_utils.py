#!/usr/bin/env python3

import logging
import re
import subprocess
from datetime import datetime
from pathlib import Path


def get_balance(account, date):
    """Get the balance for a specific account at a given date."""
    logger = logging.getLogger(__name__)
    try:
        logger.debug("🔍 Checking balance | account=%s date=%s", account, date)
        cmd = f"hledger -f all.journal bal {account} -e {date} --depth 1"
        result = subprocess.run(
            cmd.split(),
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            logger.error(
                "💔 Balance check failed | account=%s stderr=%s",
                account,
                result.stderr[:200],
            )
            return None

        logger.debug(
            "📊 Balance result | account=%s output=%s",
            account,
            result.stdout[:300],
        )

        # Extract the balance amount from the output
        lines = result.stdout.strip().split("\n")
        if lines:
            # The balance should be in the last line
            match = re.search(r"\$([0-9,.()-]+)", lines[-1])
            if match:
                return match.group(0)
        return None
    except Exception as e:
        logger.error(
            "❌ Error getting balance | account=%s error=%s",
            account,
            str(e),
            exc_info=True,
        )
        return None


def update_opening_balances(year) -> None:
    """Update opening balances in the journal file for the specified year."""
    try:
        # Calculate the previous year's end date
        prev_year = year - 1
        date = f"{prev_year}-12-31"

        # Get balances for both accounts
        bal_8542 = get_balance("assets:checking:mercury8542", date)
        bal_9281 = get_balance("assets:checking:mercury9281", date)

        if not bal_8542 or not bal_9281:
            return

        journal_file = f"{year}.journal"
        if not Path(journal_file).exists():
            return

        with open(journal_file) as f:
            content = f.read()

        # Update the balances in the opening balance transaction
        content = re.sub(
            r"(assets:checking:mercury8542\s+)= \$[0-9,.()-]+",
            f"\\1= {bal_8542}",
            content,
        )
        content = re.sub(
            r"(assets:checking:mercury9281\s+)= \$[0-9,.()-]+",
            f"\\1= {bal_9281}",
            content,
        )

        with open(journal_file, "w") as f:
            f.write(content)

    except Exception:
        pass


def main() -> None:
    current_year = datetime.now().year
    # Process years from 2022 up to and including current year + 1
    for year in range(2022, current_year + 2):
        update_opening_balances(year)


if __name__ == "__main__":
    main()
