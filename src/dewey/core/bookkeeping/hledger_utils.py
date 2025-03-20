#!/usr/bin/env python3

import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional
from dewey.core.base_script import BaseScript


class HledgerUpdater(BaseScript):
    """Updates opening balances in hledger journal files.

    Inherits from BaseScript for standardized configuration and logging.
    """

    def __init__(self) -> None:
        """Initializes the HledgerUpdater with the 'bookkeeping' config section."""
        super().__init__(config_section='bookkeeping')

    def get_balance(self, account: str, date: str) -> Optional[str]:
        """Get the balance for a specific account at a given date.

        Args:
            account: The account to check.
            date: The date to check the balance.

        Returns:
            The balance amount as a string, or None if an error occurred.
        """
        try:
            self.logger.debug("🔍 Checking balance | account=%s date=%s", account, date)
            cmd = f"hledger -f all.journal bal {account} -e {date} --depth 1"
            result = subprocess.run(
                cmd.split(),
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                self.logger.error(
                    "💔 Balance check failed | account=%s stderr=%s",
                    account,
                    result.stderr[:200],
                )
                return None

            self.logger.debug(
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
            self.logger.error(
                "❌ Error getting balance | account=%s error=%s",
                account,
                str(e),
                exc_info=True,
            )
            return None

    def update_opening_balances(self, year: int) -> None:
        """Update opening balances in the journal file for the specified year.

        Args:
            year: The year to update the opening balances for.
        """
        try:
            # Calculate the previous year's end date
            prev_year = year - 1
            date = f"{prev_year}-12-31"

            # Get balances for both accounts
            bal_8542 = self.get_balance("assets:checking:mercury8542", date)
            bal_9281 = self.get_balance("assets:checking:mercury9281", date)

            if not bal_8542 or not bal_9281:
                self.logger.warning(
                    "⚠️ Could not retrieve balances for accounts. Skipping update for year %s",
                    year,
                )
                return

            journal_file = f"{year}.journal"
            if not Path(journal_file).exists():
                self.logger.warning("Journal file %s does not exist. Skipping.", journal_file)
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
            self.logger.info("✅ Updated opening balances for year %s", year)

        except Exception as e:
            self.logger.exception(
                "🔥 Error updating opening balances for year %s: %s", year, str(e)
            )

    def run(self) -> None:
        """Runs the hledger update process for a range of years."""
        current_year = datetime.now().year
        start_year = int(self.get_config_value("start_year", 2022))
        end_year = current_year + 1

        # Process years from start_year up to and including current year + 1
        for year in range(start_year, end_year + 1):
            self.update_opening_balances(year)


def main() -> None:
    """Main entry point for the script."""
    HledgerUpdater().run()


if __name__ == "__main__":
    main()
