#!/usr/bin/env python3
"""Transaction classification feedback handler."""
from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

# Reuse existing logging configuration
from bin.logging_config import configure_logging
from classification_engine import ClassificationEngine
from journal_writer import JournalWriteError, JournalWriter

from src.utils.errors import ClassificationError, LedgerError, ValidationError

configure_logging()
logger = logging.getLogger(__name__)


class FeedbackProcessor:
    """Handles classification feedback integration with existing systems."""

    def __init__(self, rules_path: Path, journal_root: Path) -> None:
        self.engine = ClassificationEngine(rules_path)
        self.writer = JournalWriter(journal_root)
        self.audit_file = journal_root.parent / "classification_audit.log"

        # Maintain compatibility with MercuryImporter's patterns
        self.valid_categories = self.engine.categories

    def process(self, feedback: str, tx_hash: str, tx_data: dict) -> None:
        """Main processing workflow matching MercuryImporter patterns."""
        try:
            logger.info(f"Processing feedback for {tx_hash}")

            # Extract transaction context
            description = tx_data.get("description", "")
            amount = abs(float(tx_data.get("amount", 0)))

            # Validate against existing classification schema
            if not any([description, amount]):
                msg = "Missing transaction context"
                raise ValidationError(msg)

            # Process through engine's existing feedback mechanism
            self.engine.process_feedback(feedback, self.writer)

            # Log decision in audit trail
            self._log_audit_entry(tx_hash, feedback, "processed")

            logger.info("Successfully updated classification rules")

        except ClassificationError as e:
            self._log_audit_entry(tx_hash, feedback, "failed", str(e))
            raise
        except JournalWriteError as e:
            self._log_audit_entry(tx_hash, feedback, "failed", str(e))
            msg = "Journal write failed during feedback processing"
            raise LedgerError(msg) from e

    def _log_audit_entry(
        self,
        tx_hash: str,
        feedback: str,
        status: str,
        error: str | None = None,
    ) -> None:
        """Maintain audit trail compatible with MercuryImporter's AuditDB."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "tx_hash": tx_hash,
            "feedback": feedback,
            "status": status,
            "error": error,
        }

        with open(self.audit_file, "a") as f:
            f.write(json.dumps(entry) + "\n")


def main() -> None:
    """CLI interface matching mercury_import.py's argument structure."""
    parser = argparse.ArgumentParser(
        description="Process classification feedback",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("tx_hash", help="Transaction identifier from journal")
    parser.add_argument(
        "feedback",
        help="Classification feedback in format: 'pattern → account'",
    )
    parser.add_argument(
        "--rules",
        type=Path,
        default=Path("import/mercury/mercury.rules"),
        help="Classification rules file path",
    )
    parser.add_argument(
        "--journal-root",
        type=Path,
        default=Path("import/mercury/journal"),
        help="Root directory for journal files",
    )

    args = parser.parse_args()

    try:
        # In production: Load tx_data from journal using tx_hash
        # (implementation would mirror MercuryImporter's processing)
        tx_data = {
            "description": "Example Transaction",
            "amount": "0.00",
            "date": datetime.now().date().isoformat(),
        }

        processor = FeedbackProcessor(args.rules, args.journal_root)
        processor.process(args.feedback, args.tx_hash, tx_data)

    except Exception as e:
        logger.exception(f"Feedback processing failed: {e!s}")
        raise


if __name__ == "__main__":
    main()
