#!/usr/bin/env python3
import argparse
import re
import subprocess
import sys

from dewey.core.base_script import BaseScript


class FileSystemInterface:
    """Interface for file system operations."""

    def open(self, path: str, mode: str = "r") -> object:
        """Opens a file."""
        raise NotImplementedError


class RealFileSystem(FileSystemInterface):
    """Real file system operations."""

    def open(self, path: str, mode: str = "r") -> object:
        """Opens a file using the built-in open function."""
        return open(path, mode)


class SubprocessInterface:
    """Interface for subprocess operations."""

    def run(
        self, cmd: list[str], capture_output: bool, text: bool, check: bool,
    ) -> subprocess.CompletedProcess:
        """Runs a subprocess command."""
        raise NotImplementedError


class RealSubprocess(SubprocessInterface):
    """Real subprocess operations."""

    def run(
        self, cmd: list[str], capture_output: bool, text: bool, check: bool,
    ) -> subprocess.CompletedProcess:
        """Runs a subprocess command using subprocess.run."""
        return subprocess.run(
            cmd, capture_output=capture_output, text=text, check=check,
        )


class LedgerFormatChecker(BaseScript):
    """
    Validates the format of a ledger journal file.

    This class checks for various formatting issues such as date formats,
    account formats, amount formats, description lengths, and currency
    consistency. It also performs basic validation using `hledger`.
    """

    def __init__(
        self,
        journal_file: str,
        fs: FileSystemInterface | None = None,
        subprocess_runner: SubprocessInterface | None = None,
    ) -> None:
        """
        Initializes the LedgerFormatChecker.

        Args:
        ----
            journal_file: The path to the ledger journal file.
            fs: An optional FileSystemInterface for file operations.
            subprocess_runner: An optional SubprocessInterface for running subprocess commands.

        """
        super().__init__(
            name="LedgerFormatChecker",
            description="Validates the format of a ledger journal file.",
            config_section="bookkeeping",
        )
        self.journal_file = journal_file
        self.hledger_path = self.get_config_value("hledger_path", "/usr/bin/hledger")
        self.journal_content: list[str] = []
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.fs: FileSystemInterface = fs or RealFileSystem()
        self.subprocess_runner: SubprocessInterface = (
            subprocess_runner or RealSubprocess()
        )
        self.read_journal()

    def read_journal(self) -> None:
        """Reads the ledger journal file into memory."""
        self.logger.info(f"Loading journal file: {self.journal_file}")
        try:
            with self.fs.open(self.journal_file, "r") as file:
                self.journal_content = file.readlines()
        except FileNotFoundError:
            self.logger.error(f"Journal file not found: {self.journal_file}")
            self.errors.append(f"Journal file not found: {self.journal_file}")
            self.journal_content = []
        except Exception as e:
            self.logger.error(f"Error reading journal file: {e}")
            self.errors.append(f"Error reading journal file: {e}")
            self.journal_content = []

    def check_hledger_basic(self) -> bool:
        """
        Runs basic validation using `hledger`.

        Returns
        -------
            True if `hledger` validation passes

        """
        self.logger.info("Running hledger basic validation")
        try:
            result = self.subprocess_runner.run(
                [self.hledger_path, "-f", self.journal_file, "validate"],
                capture_output=True,
                text=True,
                check=True,
            )
            if result.returncode == 0:
                self.logger.info("hledger validation passed")
                return True
            self.logger.warning("hledger validation failed")
            self.warnings.append("hledger validation failed")
            return False
        except subprocess.CalledProcessError as e:
            self.logger.error(f"hledger command failed: {e}")
            self.errors.append(f"hledger command failed: {e}")
            return False
        except FileNotFoundError:
            self.logger.error(
                "hledger not found. Please ensure it is installed and in your PATH.",
            )
            self.errors.append(
                "hledger not found. Please ensure it is installed and in your PATH.",
            )
            return False

    def check_date_format(self) -> None:
        """Checks if dates are in the correct format."""
        self.logger.info("Checking date format")
        date_pattern = re.compile(r"^\d{4}[/.-]\d{2}[/.-]\d{2}")
        for i, line in enumerate(self.journal_content):
            if (
                line.strip()
                and not line.startswith((";", "!"))
                and not date_pattern.match(line)
            ):
                self.logger.warning(
                    f"Invalid date format on line {i + 1}: {line.strip()}",
                )
                self.warnings.append(
                    f"Invalid date format on line {i + 1}: {line.strip()}",
                )

    def check_accounts(self) -> None:
        """Checks if account names are in the correct format."""
        self.logger.info("Checking accounts")
        account_pattern = re.compile(r"^[A-Za-z]")
        for i, line in enumerate(self.journal_content):
            if line.strip().startswith(("Assets", "Expenses", "Income", "Liabilities")):
                if not account_pattern.match(line):
                    self.logger.warning(
                        f"Invalid account format on line {i + 1}: {line.strip()}",
                    )
                    self.warnings.append(
                        f"Invalid account format on line {i + 1}: {line.strip()}",
                    )

    def check_amount_format(self) -> None:
        """Checks if amounts are in the correct format."""
        self.logger.info("Checking amount format")
        amount_pattern = re.compile(r"[-+]?\s*\d+(?:,\d{3})*(?:\.\d{2})?\s*[A-Z]{3}")
        for i, line in enumerate(self.journal_content):
            if re.search(r"\s+-?\s*\d", line) and not amount_pattern.search(line):
                self.logger.warning(
                    f"Invalid amount format on line {i + 1}: {line.strip()}",
                )
                self.warnings.append(
                    f"Invalid amount format on line {i + 1}: {line.strip()}",
                )

    def check_description_length(self) -> None:
        """Checks if descriptions exceed the maximum allowed length."""
        self.logger.info("Checking description length")
        max_length: int = self.get_config_value("max_description_length", 50)
        for i, line in enumerate(self.journal_content):
            parts = line.split("  ")
            if len(parts) > 1 and len(parts[0]) > max_length:
                self.logger.warning(
                    f"Description too long on line {i + 1}: {line.strip()}",
                )
                self.warnings.append(
                    f"Description too long on line {i + 1}: {line.strip()}",
                )

    def check_currency_consistency(self) -> None:
        """Checks if all transactions use the same currency."""
        self.logger.info("Checking currency consistency")
        currency_pattern = re.compile(r"[A-Z]{3}")
        first_currency: str | None = None

        for i, line in enumerate(self.journal_content):
            if re.search(r"\s+-?\s*\d", line):
                match = currency_pattern.search(line)
                if match:
                    currency = match.group(0)
                    if first_currency is None:
                        first_currency = currency
                    elif currency != first_currency:
                        self.logger.warning(
                            f"Currency inconsistency on line {i + 1}: {line.strip()} (expected {first_currency})",
                        )
                        self.warnings.append(
                            f"Currency inconsistency on line {i + 1}: {line.strip()} (expected {first_currency})",
                        )

    def run_all_checks(self) -> bool:
        """
        Runs all validation checks.

        Returns
        -------
            True if all checks pass without errors, False otherwise.

        """
        self.logger.info("Starting ledger validation checks")
        hledger_check = self.check_hledger_basic()
        self.check_date_format()
        self.check_accounts()
        self.check_amount_format()
        self.check_description_length()
        self.check_currency_consistency()

        if self.errors:
            return False
        return hledger_check

    def execute(self) -> bool:
        """Runs the ledger format checker."""
        if self.run_all_checks():
            return True
        if self.errors:
            return False
        return False


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Validate ledger journal file format.")
    parser.add_argument("journal_file", help="Path to the ledger journal file")
    args = parser.parse_args()

    checker = LedgerFormatChecker(args.journal_file)
    if not checker.run():
        sys.exit(1)


if __name__ == "__main__":
    main()
