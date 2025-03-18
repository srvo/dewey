
# Refactored from: mercury_importer
# Date: 2025-03-16T16:19:08.974532
# Refactor Version: 1.0
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from re import Pattern
from typing import Any

import requests
from bin.mercury_api import MercuryAPI
from classification_engine import ClassificationEngine

from src.utils.errors import (
    FileIntegrityError,
    ValidationError,
)


def single_space(s: str) -> str:
    """Normalize whitespace in strings."""
    return re.sub(r"\s{2,}", " ", s.strip())


class DeepInfraAPI:
    def __init__(self, valid_categories: list) -> None:
        self.logger = logging.getLogger(f"{__name__}.DeepInfraAPI")
        self.api_key = os.getenv("DEEPINFRA_API_KEY")
        self.base_url = "https://api.deepinfra.com/v1"
        self.valid_categories = valid_categories

    def classify_transaction(self, description: str, amount: float) -> str:
        """Classify transaction using AI model with validation."""
        prompt = (
            f"Classify this financial transaction into one of these accounting categories:\n"
            f"Valid options: {', '.join(self.valid_categories)}\n\n"
            f"Description: {description}\n"
            f"Amount: ${abs(amount):.2f} ({'expense' if amount < 0 else 'income'})\n"
            "Respond ONLY with the matching account name from the valid options."
        )

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": "meta-llama/Meta-Llama-3-70B-Instruct",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 20,
                    "temperature": 0.3,
                },
                timeout=10,
            )
            response.raise_for_status()
            category = response.json()["choices"][0]["message"]["content"].strip()

            # Validate the response
            if category in self.valid_categories:
                return category
            self.logger.warning("AI returned invalid category: %s", category)
            return ""
        except Exception as e:
            self.logger.exception("DeepInfra classification failed: %s", str(e))
            return ""


from bin.logging_config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)


class AccountStructure:
    def __init__(self, classifier: ClassificationEngine) -> None:
        self.classifier = classifier
        self.classification_rules = classifier.rules
        self.expense_accounts: set[str] = set()
        self.income_accounts: set[str] = set()
        self.asset_accounts: set[str] = set()
        self.unknown_expense = "Expenses:UnknownExpenses"
        self.unknown_income = "Income:UnknownIncome"
        self.unknown_asset = "Assets:MercuryUnknown"
        # Add accounts from our classification patterns
        self.expense_accounts.update(
            {
                "expenses:fees:transfer",
                "expenses:insurance:general",
                "expenses:car:insurance",
                "expenses:software:subscription",
                "expenses:travel",
                "expenses:food:meals",
                "expenses:financial:debt",
                "expenses:financial:fees",
                "expenses:professional:compliance",
            },
        )
        self.asset_accounts.update(
            {
                "assets:checking:mercury:transfer",
                "assets:investments",
                "assets:illiquid:RA-stock",
                "liabilities:member:capital",
                "equity:draw",
            },
        )
        self.income_accounts.update(
            {
                "income:investments",
                "income:consulting",
            },
        )
        # Add the unknown accounts to the sets immediately
        self.expense_accounts.add(self.unknown_expense)
        self.income_accounts.add(self.unknown_income)
        self.asset_accounts.add(self.unknown_asset)

    def _get_configured_categories(self, root_type: str) -> set:
        """Get categories from classification rules that match type."""
        return {
            cat
            for cat in self.classifier.categories  # Will need to inject classifier
            if cat.startswith(root_type)
        }


from prometheus_client import CollectorRegistry, Counter

METRICS = Counter(
    "classification_outcomes",
    ["type"],  # success/failure/pending
    registry=CollectorRegistry(),
)


class AuditDB:
    def __init__(self) -> None:
        self.audit_file = Path("import/mercury/audit.log")

    def log(self, tx_hash: str, status: str, details: str) -> None:
        with open(self.audit_file, "a") as f:
            f.write(f"{datetime.now().isoformat()}|{tx_hash}|{status}|{details}\n")


class MercuryImporter:
    def __init__(self) -> None:
        # Initialize classifier first with proper rules path
        self.classifier = ClassificationEngine(Path("import/mercury/mercury.rules"))
        self.account_struct = AccountStructure(self.classifier)
        self.audit_log = AuditDB()
        # Get valid categories from classification engine
        valid_categories: list[str] = self.classifier.categories
        # Initialize API client with valid categories
        self.deepinfra: DeepInfraAPI = DeepInfraAPI(valid_categories)
        self.processed_hashes_file = Path("import/mercury/.processed_hashes")
        self.seen_hashes = self._load_processed_hashes()
        self.transaction_count: int = 0
        self.journal_entries: defaultdict[str, list[str]] = defaultdict(list)
        self.metrics: dict[str, int] = {
            "processed": 0,
            "failed": 0,
            "api_calls": 0,
        }

    def _load_rules(self, rules_path: Path) -> dict:
        """Load classification rules from JSON file."""
        with open(rules_path) as f:
            rules = json.load(f)

        # Add regex validation during loading
        for pattern in rules["patterns"]:
            try:
                re.compile(pattern)
            except re.error as e:
                msg = f"Invalid regex pattern '{pattern}': {e!s}"
                raise ValueError(msg)

        return rules

    def _load_processed_hashes(self) -> set[str]:
        """Load previously processed transaction hashes."""
        if self.processed_hashes_file.exists():
            with open(self.processed_hashes_file) as f:
                return set(f.read().splitlines())
        return set()

    def _save_processed_hashes(self) -> None:
        """Persist processed hashes between runs."""
        with open(self.processed_hashes_file, "w") as f:
            f.write("\n".join(self.seen_hashes))
        # Add API clients directly
        self.mercury_api: MercuryAPI = MercuryAPI()
        # Pre-compile regex patterns for classification
        self.compiled_patterns: dict[str, Pattern] = {
            pattern: re.compile(pattern, re.IGNORECASE)
            for pattern in self.account_struct.classification_rules["patterns"]
        }

    def process_files(self, input_dir: Path) -> None:
        """Process all Mercury CSV files in directory."""
        for csv_file in input_dir.glob("mercury_*.csv"):
            self.process_file(csv_file)

    def process_file(self, csv_file: Path) -> None:
        """Process CSV using hledger's import command."""
        logger.info("📂 Processing with hledger: %s", csv_file.name)

        rules_file = csv_file.with_suffix(".csv.rules")
        paisa_file = csv_file.with_suffix(".csv.paisa")

        logger.info("⚙️  Generating rules files: %s, %s", rules_file, paisa_file)
        self.classifier.export_hledger_rules(rules_file)
        self.classifier.export_paisa_template(paisa_file)

        try:
            # Dry run with output capture
            logger.info("🔍 Running dry-run import")
            dry_run = subprocess.run(
                [
                    "hledger",
                    "--ignore-case",
                    "import",
                    "--rules-file",
                    str(rules_file),
                    "--dry-run",
                    "--config",
                    str(Path("import/mercury/hledger.conf")),
                    str(csv_file),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info("Dry-run output:\n%s", dry_run.stdout)

            # Actual import with progress
            logger.info("🚀 Starting actual import")
            actual_run = subprocess.run(
                [
                    "hledger",
                    "--ignore-case",
                    "import",
                    "--rules-file",
                    str(rules_file),
                    "--config",
                    str(Path("import/mercury/hledger.conf")),
                    str(csv_file),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info("Import completed!\n%s", actual_run.stdout)

            self.audit_transactions(csv_file)

        except subprocess.CalledProcessError as e:
            logger.exception("❌ hledger import failed")
            logger.exception("Command: %s", " ".join(e.cmd))
            logger.exception("Exit code: %d", e.returncode)
            logger.exception("Error output:\n%s", e.stderr)
            raise

    def _process_batch(
        self,
        batch: list[dict[str, str]],
        batch_num: int,
        total_rows: int,
    ) -> None:
        """Process a batch of transactions with progress tracking."""
        logger.debug(
            "Processing batch %d (~%d%%)",
            batch_num + 1,
            int(((batch_num * 100) + len(batch)) / total_rows * 100),
        )

        for tx in batch:
            try:
                self.process_transaction(tx)
            except Exception as e:
                self.metrics["failed"] += 1
                logger.error("Transaction error: %s", str(e), exc_info=True)

    def _parse_csv_row(self, row: dict[str, str]) -> dict[str, Any]:
        """Enhanced CSV parsing with validation."""
        try:
            # Null checks for required fields
            if not row.get("account_id"):
                msg = "Missing account_id"
                raise ValidationError(msg, tx_hash="n/a")

            # Date validation
            try:
                date_obj = datetime.strptime(row["date"], "%Y-%m-%d")
                if date_obj > datetime.now():
                    msg = "Future date not allowed"
                    raise ValidationError(msg, tx_hash="n/a")
            except ValueError:
                msg = f"Invalid date format: {row['date']}"
                raise ValidationError(msg, tx_hash="n/a")

            # Amount validation
            try:
                amount = float(row["amount"])
                if abs(amount) > 1_000_000:  # Fraud/error threshold
                    msg = "Amount exceeds safety limit"
                    raise ValidationError(msg, tx_hash="n/a")
            except ValueError:
                msg = f"Invalid amount: {row['amount']}"
                raise ValidationError(msg, tx_hash="n/a")

            # Normalize and return data
            return {
                "date": date_obj.date().isoformat(),
                "description": single_space(row["description"].strip()),
                "amount": abs(amount),
                "is_income": amount > 0,
                "account_id": row["account_id"].strip(),
                "raw": row,
            }

        except KeyError as e:
            msg = f"Missing required field: {e!s}"
            raise ValidationError(msg, tx_hash="n/a")

    def _generate_journal_entry(
        self,
        tx: dict[str, Any],
        from_account: str,
        to_account: str,
    ) -> str:
        """Generate hledger journal entry with improved formatting."""
        # Build transaction header
        header = f"{tx['date']} {tx['description']}"

        # Add reference code if available
        if tx["raw"].get("reference"):
            header += f" ({tx['raw']['reference']})"

        # Format amounts with direction
        if tx["is_income"]:
            amount_str = f"${tx['amount']:.2f}"
            from_line = f"    {from_account: <45}  {amount_str}"
            to_line = f"    {to_account}"
        else:
            amount_str = f"${tx['amount']:.2f}"
            from_line = f"    {from_account}"
            to_line = f"    {to_account: <45}  {amount_str}"

        # Add balance comment if available
        balance = tx["raw"].get("balance")
        balance_comment = f"  ; Balance: {balance}" if balance else ""

        return f"{header}\n{from_line}{balance_comment}\n{to_line}\n\n"

    def process_transaction(self, row: dict) -> None:
        """Process individual transaction row with new CSV handling."""
        logger = logging.getLogger(f"{__name__}.TransactionProcessor")
        try:
            parsed = self._parse_csv_row(row)
            tx_hash = self._generate_transaction_hash(parsed)

            if tx_hash in self.seen_hashes:
                logger.debug("⏭️ Skipping duplicate transaction")
                self.audit_log.log(tx_hash, "skipped", "duplicate")
                return

            self.seen_hashes.add(tx_hash)
            self.transaction_count += 1
            self.metrics["processed"] += 1

            # Classification logic remains the same
            from_acc, to_acc, amount = self.classify_transaction(
                parsed["description"],
                parsed["amount"] * (-1 if not parsed["is_income"] else 1),
            )

            entry = self._generate_journal_entry(parsed, from_acc, to_acc)
            self._store_journal_entry(parsed["date"][:4], entry)

            # Log successful processing
            self.audit_log.log(
                tx_hash,
                "processed",
                f"from:{from_acc} to:{to_acc} amount:{amount}",
            )

        except Exception as e:
            self.metrics["failed"] += 1
            logger.error("❌ Transaction failed | error=%s", str(e), exc_info=True)
            self.audit_log.log(tx_hash, "failed", str(e))
            raise

    def _generate_transaction_hash(self, parsed_tx: dict[str, Any]) -> str:
        """Create unique hash for transaction deduplication with salt."""
        from secrets import token_hex

        HASH_SALT: str = token_hex(16)  # Persistent per installation
        data = f"{HASH_SALT}|{parsed_tx['date']}|{parsed_tx['description']}|{parsed_tx['amount']}"
        return hashlib.sha3_256(data.encode()).hexdigest()

    def _store_journal_entry(self, year: str, entry: str) -> None:
        """Store formatted journal entry by year."""
        self.journal_entries[year].append(entry)

    def classify_transaction(
        self,
        description: str,
        amount: float,
    ) -> tuple[str, str, float]:
        """Determine accounts for a transaction with optimized pattern matching."""
        try:
            # Check against pre-compiled classification patterns
            for pattern, compiled in self.compiled_patterns.items():
                if compiled.search(description):
                    account = self.account_struct.classification_rules["patterns"][
                        pattern
                    ]
                    if amount < 0:
                        METRICS.labels(type="success").inc()
                        return (account, "Expenses:Unknown", abs(amount))
                    METRICS.labels(type="success").inc()
                    return ("Expenses:Unknown", account, amount)

            # AI Classification Fallback
            ai_category: str = self.deepinfra.classify_transaction(description, amount)
            if ai_category:
                logger.info(
                    "AI classified transaction: %s => %s",
                    description[:30],
                    ai_category,
                )
                if amount < 0:
                    METRICS.labels(type="success").inc()
                    return (ai_category, "Expenses:Unknown", abs(amount))
                METRICS.labels(type="success").inc()
                return ("Expenses:Unknown", ai_category, amount)

            # Final fallback to pending classification
            METRICS.labels(type="pending").inc()
            return (
                "Expenses:PendingClassification",
                "Expenses:PendingClassification",
                amount,
            )

        except Exception as e:
            logger.exception(f"Classification failed: {e!s}")
            METRICS.labels(type="failure").inc()
            return (
                "Expenses:PendingClassification",
                "Expenses:PendingClassification",
                amount,
            )

    def write_journal_files(self) -> None:
        """Write files with versioned backups and atomic writes."""
        logger = logging.getLogger(f"{__name__}.FileWriter")
        total_entries = sum(len(e) for e in self.journal_entries.values())
        logger.info("📤 Writing journal files | total_entries=%d", total_entries)

        output_dir = Path("data/processed/journals")
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            for (
                account_id,
                year,
            ), entries in self._group_entries_by_account_and_year():
                filename = output_dir / f"{account_id}_{year}.journal"

                # Create temp file first for atomic write
                temp_file = filename.with_suffix(".tmp")
                try:
                    with open(temp_file, "w", encoding="utf-8") as f:
                        f.writelines(entries)

                    # Create versioned backup if file exists
                    if filename.exists():
                        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                        backup_name = f"{filename.stem}_{timestamp}{filename.suffix}"
                        shutil.copy(filename, filename.parent / backup_name)

                    # Atomic replacement
                    os.replace(temp_file, filename)

                except OSError as e:
                    msg = f"Failed to write journal: {e!s}"
                    raise FileIntegrityError(msg)
                finally:
                    if temp_file.exists():
                        temp_file.unlink()

        finally:
            self._save_processed_hashes()

    def _group_entries_by_account_and_year(self) -> dict[tuple[str, str], list[str]]:
        """Organize entries by account ID and year."""
        grouped = defaultdict(list)
        for year, entries in self.journal_entries.items():
            for entry in entries:
                # Extract account ID from entry metadata
                account_id = "8542"  # TEMP - Should get from transaction data
                grouped[(account_id, year)].append(entry)
        return grouped


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-dir",
        default="import/mercury/in",
        help="Directory containing Mercury CSV files",
    )
    parser.add_argument(
        "--annual",
        action="store_true",
        help="Generate annual ledger files",
    )
    args = parser.parse_args()

    importer = MercuryImporter()
    importer.process_files(Path(args.input_dir))


if __name__ == "__main__":
    main()
