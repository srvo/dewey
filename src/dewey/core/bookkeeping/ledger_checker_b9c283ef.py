#!/usr/bin/env python3
import logging

# ... other imports remain unchanged ...


class LedgerFormatChecker:
    def __init__(self, journal_file: str) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        # ... rest of init ...

    def read_journal(self) -> None:
        self.logger.info("Loading journal file: %s", self.journal_file)
        # ... rest of method ...

    def check_hledger_basic(self) -> bool:
        self.logger.info("Running hledger basic validation")
        # ... rest of method ...

    # ... modify all check methods to use logger instead of print ...

    def run_all_checks(self) -> bool:
        self.logger.info("Starting ledger validation checks")
        # ... rest of method ...


def main() -> None:
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger(__name__)

    # ... rest of main logic ...

    if checker.warnings:
        logger.warning("Validation warnings occurred")

    if checker.errors:
        logger.error("Validation errors detected")
        sys.exit(1)

    logger.info("All ledger checks passed successfully")


# ... rest of original code ...
