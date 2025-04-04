#!/usr/bin/env python3

import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from dewey.core.base_script import BaseScript


class SubprocessRunnerInterface(Protocol):
    """Interface for running subprocess commands."""

    def __call__(
        self,
        args: list[str],
        capture_output: bool = True,
        text: bool = True,
        check: bool = False,
    ) -> subprocess.CompletedProcess: ...


class FileSystemInterface(Protocol):
    """Interface for file system operations."""

    def exists(self, path: Path | str) -> bool: ...

    def open(self, path: Path | str, mode: str = "r") -> Any: ...


class HledgerUpdaterInterface(Protocol):
    """Interface for HledgerUpdater."""

    def get_balance(self, account: str, date: str) -> str | None: ...

    def update_opening_balances(self, year: int) -> None: ...

    def run(self) -> None: ...


class HledgerUpdater(BaseScript, HledgerUpdaterInterface):
    """
    Updates opening balances in hledger journal files.

    Inherits from BaseScript for standardized configuration and logging.
    """

    def __init__(
        self,
        subprocess_runner: SubprocessRunnerInterface | None = None,
        fs: FileSystemInterface | None = None,
    ) -> None:
        """Initializes the HledgerUpdater with the 'bookkeeping' config section."""
        super().__init__(config_section="bookkeeping")
        self._subprocess_runner = subprocess_runner or subprocess.run
        self._fs = fs or PathFileSystem()

    def get_balance(self, account: str, date: str) -> str | None:
        """
        Get the balance for a specific account at a given date.

        Args:
        ----
            account: The account to check.
            date: The date to check the balance.

        Returns:
        -------
            The balance amount as a string, or None if an error occurred.

        """
        try:
            self.logger.debug("🔍 Checking balance | account=%s date=%s", account, date)
            cmd = f"hledger -f all.journal bal {account} -e {date} --depth 1"
            result = self._subprocess_runner(
                cmd.split(), capture_output=True, text=True, check=False,
            )

            if result.returncode != 0:
                self.logger.error(
                    "💔 Balance check failed | account=%s stderr=%s",
                    account,
                    result.stderr[:200],
                )
                return None

            self.logger.debug(
                "📊 Balance result | account=%s output=%s", account, result.stdout[:300],
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

    def _read_journal_file(self, journal_file: str) -> str:
        """
        Reads the content of the journal file.

        Args:
        ----
            journal_file: The path to the journal file.

        Returns:
        -------
            The content of the journal file.

        """
        with self._fs.open(journal_file) as f:
            content = f.read()
        return content

    def _write_journal_file(self, journal_file: str, content: str) -> None:
        """
        Writes the content to the journal file.

        Args:
        ----
            journal_file: The path to the journal file.
            content: The content to write to the file.

        """
        with self._fs.open(journal_file, "w") as f:
            f.write(content)

    def update_opening_balances(self, year: int) -> None:
        """
        Update opening balances in the journal file for the specified year.

        Args:
        ----
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
            if not self._fs.exists(journal_file):
                self.logger.warning(
                    "Journal file %s does not exist. Skipping.", journal_file,
                )
                return

            content = self._read_journal_file(journal_file)

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

            self._write_journal_file(journal_file, content)
            self.logger.info("✅ Updated opening balances for year %s", year)

        except Exception as e:
            self.logger.exception(
                "🔥 Error updating opening balances for year %s: %s", year, str(e),
            )

    def execute(self) -> None:
        """Runs the hledger update process for a range of years."""
        current_year = datetime.now().year
        start_year = int(self.get_config_value("start_year", 2022))
        end_year = current_year + 1

        # Process years from start_year up to and including current year + 1
        for year in range(start_year, end_year + 1):
            self.update_opening_balances(year)


class PathFileSystem:
    """A real file system implementation using pathlib.Path."""

    def exists(self, path: Path | str) -> bool:
        """Check if a path exists."""
        return Path(path).exists()

    def open(self, path: Path | str, mode: str = "r"):
        """Open a file."""
        return open(path, mode)


def main() -> None:
    """Main entry point for the script."""
    HledgerUpdater().run()


if __name__ == "__main__":
    main()
