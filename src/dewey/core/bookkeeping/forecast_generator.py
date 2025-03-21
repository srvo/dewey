import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Protocol, Tuple

from dateutil.relativedelta import relativedelta

from dewey.core.base_script import BaseScript


class FileSystemInterface(Protocol):
    """Interface for file system operations."""

    def open(self, path: str, mode: str = "r") -> object:
        """Open a file."""

    def exists(self, path: str) -> bool:
        """Check if a file exists."""


class RealFileSystem:
    """Real file system operations."""

    def open(self, path: str, mode: str = "r") -> object:
        """Open a file."""
        return open(path, mode)

    def exists(self, path: str) -> bool:
        """Check if a file exists."""
        return Path(path).exists()


class JournalEntryGenerator(BaseScript):
    """Generates journal entries for the Mormair_E650 asset, including
    acquisition, depreciation, lease income, revenue sharing, and hosting fees.
    """

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

    def __init__(self, fs: FileSystemInterface = RealFileSystem()) -> None:
        """Initializes the JournalEntryGenerator with bookkeeping configurations."""
        super().__init__(config_section="bookkeeping")
        self.fs: FileSystemInterface = fs

    def validate_assumptions(self) -> None:
        """Validates key assumptions with user input.

        Raises:
            SystemExit: If the user does not confirm an assumption.
        """
        try:
            for i, assumption in enumerate(self.ASSUMPTIONS, 1):
                while True:
                    response = input(f"{i}. {assumption} (y/n): ").strip().lower()
                    if response == "y":
                        break
                    if response == "n":
                        sys.exit()
                    else:
                        self.logger.warning("Invalid input. Please enter 'y' or 'n'.")
        except Exception as e:
            self.logger.exception(f"Error during assumption validation: {e!s}")
            sys.exit(1)

    def create_acquisition_entry(self, acquisition_date: date) -> str:
        """Create the acquisition journal entry.

        Args:
            acquisition_date: The date of the asset acquisition.

        Returns:
            The formatted acquisition journal entry string.
        """
        return f"""\
{acquisition_date.strftime('%Y-%m-%d')} Acquired Mormair_E650 via barter
    Assets:PPE:Mormair_E650             £2500.00
    Assets:Cash                            £-25.00
    Income:Consulting:Services          £-2475.00

"""

    def append_acquisition_entry(
        self, complete_ledger_file: str, acquisition_entry: str
    ) -> None:
        """Append the acquisition entry to the complete ledger file if it doesn't
        already exist.

        Args:
            complete_ledger_file: Path to the complete ledger file.
            acquisition_entry: The acquisition journal entry string.
        """
        acquisition_entry_exists = False
        try:
            with self.fs.open(complete_ledger_file) as f:  # type: ignore
                if acquisition_entry in f.read():
                    acquisition_entry_exists = True
        except FileNotFoundError:
            self.logger.warning(f"File not found: {complete_ledger_file}")
            pass  # Handle missing file gracefully
        except Exception as e:
            self.logger.error(f"Error reading file: {e}")
            return

        if not acquisition_entry_exists:
            try:
                with self.fs.open(complete_ledger_file, "a") as f:  # type: ignore
                    f.write(acquisition_entry)
            except Exception as e:
                self.logger.error(f"Error writing to file: {e}")

    def initialize_forecast_ledger(self, forecast_ledger_file: str) -> None:
        """Initializes the forecast ledger file with account declarations if it
        doesn't exist.

        Args:
            forecast_ledger_file: Path to the forecast ledger file.
        """
        try:
            if not self.fs.exists(forecast_ledger_file):
                with self.fs.open(forecast_ledger_file, "w") as f:  # type: ignore
                    account_declarations = """
; Account declarations
account Assets:PPE:Mormair_E650
account Assets:Cash
account Income:Consulting:Services
account Expenses:Depreciation:Mormair_E650
account Assets:AccumulatedDepr:Mormair_E650
account Income:Lease:Mormair_E650
account Expenses:RevenueShare:Mormair_E650
account Expenses:Hosting:Mormair_E650
"""
                    f.write(account_declarations)
        except Exception as e:
            self.logger.error(f"Error initializing forecast ledger: {e}")
            raise

    def create_depreciation_entry(self, current_date: datetime) -> str:
        """Create a depreciation journal entry for a given date.

        Args:
            current_date: The date for which to create the depreciation entry.

        Returns:
            The formatted depreciation journal entry string.
        """
        return (
            f"{current_date.strftime('%Y-%m-%d')} Depreciation - Mormair_E650\n"
            "    Expenses:Depreciation:Mormair_E650     £6.94\n"
            "    Assets:AccumulatedDepr:Mormair_E650   £-6.94\n\n"
        )

    def calculate_revenue_share(self, recovered: float) -> float:
        """Calculates the revenue share based on the recovered amount."""
        if recovered < 125975:
            revenue_share = 0.5
        elif recovered < 359975:
            revenue_share = 0.01
        else:
            revenue_share = 0
        return revenue_share

    def create_revenue_entries(
        self,
        current_date: datetime,
        generator: Dict[str, Any],
    ) -> Tuple[str, str, str]:
        """Creates revenue-related journal entries (lease income, revenue share,
        hosting fee).

        Args:
            current_date: The date for which to create the entries.
            generator: A dictionary containing revenue recovery information.

        Returns:
            A tuple containing the lease income, revenue share payment, and
            hosting fee payment entries.
        """
        gross_revenue = 302495
        revenue_share = self.calculate_revenue_share(generator["recovered"])
        revenue_share_amount = gross_revenue * revenue_share
        hosting_fee = gross_revenue * 0.25

        generator["recovered"] += revenue_share_amount
        generator["recovered"] = min(generator["recovered"], 359975)

        lease_income_entry = (
            f"{current_date.strftime('%Y-%m-%d')} Lease income - Mormair_E650\n"
            f"    Assets:Cash                          £{gross_revenue - revenue_share_amount - hosting_fee:.2f}\n"
            f"    Income:Lease:Mormair_E650          £-{gross_revenue:.2f}\n\n"
        )

        revenue_share_payment_entry = (
            f"{current_date.strftime('%Y-%m-%d')} Revenue share payment - "
            f"Mormair_E650\n"
            f"    Expenses:RevenueShare:Mormair_E650  £{revenue_share_amount:.2f}\n"
            f"    Assets:Cash                           £-{revenue_share_amount:.2f}\n\n"
        )

        hosting_fee_payment_entry = (
            f"{current_date.strftime('%Y-%m-%d')} Hosting fee payment - "
            f"Mormair_E650\n"
            f"    Expenses:Hosting:Mormair_E650        £{hosting_fee:.2f}\n"
            f"    Assets:Cash                           £-{hosting_fee:.2f}\n\n"
        )

        return (
            lease_income_entry,
            revenue_share_payment_entry,
            hosting_fee_payment_entry,
        )

    def write_journal_entry(self, file_path: str, entry: str) -> None:
        """Writes a journal entry to the specified file."""
        try:
            with self.fs.open(file_path, "a") as f:
                f.write(entry)
        except Exception as e:
            self.logger.error(f"Error writing to file: {e}")
            raise

    def generate_journal_entries(
        self,
        complete_ledger_file: str,
        forecast_ledger_file: str,
    ) -> None:
        """Generates journal entries and appends them to the journal files.

        Args:
            complete_ledger_file: Path to the complete ledger file.
            forecast_ledger_file: Path to the forecast ledger file.
        """
        acquisition_date_str = "2023-12-01"
        acquisition_date = datetime.strptime(acquisition_date_str, "%Y-%m-%d").date()

        acquisition_entry = self.create_acquisition_entry(acquisition_date)
        self.append_acquisition_entry(complete_ledger_file, acquisition_entry)

        self.initialize_forecast_ledger(forecast_ledger_file)

        generators = [{"recovered": 0, "last_revenue": 0}]
        current_date = datetime(2026, 12, 31)
        end_date = datetime(2056, 12, 31)

        while current_date <= end_date:
            depreciation_entry = self.create_depreciation_entry(current_date)
            self.write_journal_entry(forecast_ledger_file, depreciation_entry)

            for generator in generators:
                (
                    lease_income_entry,
                    revenue_share_payment_entry,
                    hosting_fee_payment_entry,
                ) = self.create_revenue_entries(current_date, generator)

                self.write_journal_entry(forecast_ledger_file, lease_income_entry)
                self.write_journal_entry(forecast_ledger_file, revenue_share_payment_entry)
                self.write_journal_entry(forecast_ledger_file, hosting_fee_payment_entry)

            current_date += relativedelta(months=1)
            current_date = current_date.replace(day=1) + relativedelta(
                months=1, days=-1
            )

    def run(self) -> None:
        """Runs the journal entry generation process."""
        complete_ledger_file = self.get_config_value(
            "bookkeeping.complete_ledger_file", ""
        )
        forecast_ledger_file = self.get_config_value(
            "bookkeeping.forecast_ledger_file", ""
        )

        self.validate_assumptions()
        self.generate_journal_entries(
            complete_ledger_file,
            forecast_ledger_file,
        )


if __name__ == "__main__":
    generator = JournalEntryGenerator()
    parser = generator.setup_argparse()
    parser.description = "Generate journal entries for Mormair_E650 asset"
    parser.add_argument(
        "complete_ledger_file",
        help="Path to the complete_ledger.journal file",
    )
    parser.add_argument("forecast_ledger_file", help="Path to the forecast.ledger file")
    args = parser.parse_args()

    # generator.complete_ledger_file = args.complete_ledger_file
    # generator.forecast_ledger_file = args.forecast_ledger_file

    generator.execute()
