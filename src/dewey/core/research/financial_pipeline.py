
# Refactored from: financial_pipeline
# Date: 2025-03-16T16:19:10.997342
# Refactor Version: 1.0
#!/usr/bin/env python3
import logging
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Configure logging to match script output style
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def check_account_declarations(main_ledger: Path) -> None:
    """Verify required accounts are declared in the main ledger file.

    Args:
    ----
        main_ledger: Path to the main ledger file.

    """
    logger.info("\n=== ACCOUNT DECLARATIONS ===")

    # Update path to match MercuryImporter's output location
    journal_dir = Path("data/processed/journals")
    mercury_journals = list(journal_dir.glob("*.journal"))

    if not journal_dir.exists():
        logger.error("Journal directory missing: %s", journal_dir.resolve())
        logger.error("Please verify transaction processing completed successfully")
        sys.exit(1)

    if not mercury_journals:
        logger.error("No journal files found in %s", journal_dir)
        logger.error("Directory contents:")
        result = subprocess.run(
            ["ls", "-la", str(journal_dir)],
            capture_output=True,
            text=True,
            check=False,
        )
        logger.error(result.stdout or "Directory empty")
        sys.exit(1)

    required_accounts = ["Expenses:Insurance", "Expenses:Payroll:Salaries"]

    try:
        # Check accounts using both main ledger and generated journals
        files = [str(main_ledger)] + [str(p) for p in mercury_journals]
        result = subprocess.run(
            ["hledger", "accounts", "-f", ",".join(files), "--declared"],
            capture_output=True,
            text=True,
            check=True,
        )
        declared_accounts = set(result.stdout.splitlines())

        missing = []
        for acc in required_accounts:
            if acc not in declared_accounts:
                missing.append(acc)
                logger.error("Account not declared: %s", acc)

        if missing:
            logger.error("\nERROR: Missing account declarations in %s", main_ledger)
            logger.error("Add these to your journal file with 'account' directives:")
            for acc in missing:
                logger.error("account %s", acc)
            logger.error("\nExample:\n")
            for acc in missing:
                logger.error("account %s  ; Add proper opening balance if needed", acc)
            sys.exit(1)

        logger.info("All required accounts are properly declared in %s", main_ledger)

    except subprocess.CalledProcessError as e:
        logger.exception("Failed to check account declarations: %s", e.stderr)
        sys.exit(1)


def system_checks() -> None:
    """Verify required dependencies are installed."""
    logger.info("=== SYSTEM CHECKS ===")
    required = ["hledger", "python3"]
    missing = [cmd for cmd in required if not shutil.which(cmd)]

    if missing:
        logger.error("Error: Missing required commands: %s", ", ".join(missing))
        sys.exit(1)


def check_python_dependencies() -> None:
    """Verify required Python packages are installed."""
    logger.info("\n=== PYTHON DEPENDENCIES ===")
    required = ["requests", "colorlog", "dotenv"]  # Changed python_dotenv -> dotenv
    missing = []

    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)

    if missing:
        logger.error("Missing Python packages: %s", ", ".join(missing))
        logger.error("Install with: pip3 install -r requirements.txt")
        sys.exit(1)


def run_repository_maintenance() -> None:
    """Run repository maintenance checks."""
    logger.info("\n=== REPOSITORY MAINTENANCE ===")
    for check_arg in ["--check-requirements", "--check-duplicates"]:
        result = subprocess.run(
            ["python3", "repo_maintenance.py", check_arg],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            logger.error("Maintenance check failed: %s", check_arg)
            logger.error(result.stderr)
            sys.exit(1)


def process_transactions(mercury_input_dir: Path) -> None:
    """Handle Mercury transaction processing with single process.

    Args:
    ----
        mercury_input_dir: Path to the Mercury input directory.

    """
    logger.info("\n=== PROCESSING TRANSACTIONS ===")

    try:
        if not mercury_input_dir.exists():
            msg = f"Mercury input directory not found: {mercury_input_dir}"
            raise FileNotFoundError(
                msg,
            )

        # Check if processing is needed
        csv_files = [
            f for f in mercury_input_dir.glob("mercury_*.csv") if f.stat().st_size > 500
        ]
        logger.info("Found %d CSV files needing processing", len(csv_files))

        # Show detected files
        logger.debug("Files to process:")
        for i, f in enumerate(csv_files, 1):
            logger.debug("%2d. %s", i, f.name)

        start_time = datetime.now()
        result = subprocess.run(
            [
                "python3",
                "mercury_import.py",
                "--input-dir",
                str(mercury_input_dir),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        duration = datetime.now() - start_time

        logger.info("Processing finished in %s", duration)
        logger.debug("Complete stdout:\n%s", result.stdout)

        if result.returncode != 0:
            logger.error("❌ Processing failed after %s", duration)
            logger.error("Error output:\n%s", result.stderr)

            # New hledger validation check
            journal_dir = Path("import/mercury/journal/by_year")
            if journal_dir.exists():
                logger.info("\nRunning hledger validation on generated files:")
                for jfile in journal_dir.glob("*.journal"):
                    result = subprocess.run(
                        ["hledger", "-f", str(jfile), "check"],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if result.returncode == 0:
                        logger.info("✅ %s: Valid", jfile.name)
                    else:
                        logger.error("❌ %s: Invalid\n%s", jfile.name, result.stderr)

            sys.exit(1)

        logger.info("✅ Completed all files in %s", duration)

    except Exception as e:
        logger.exception("Transaction processing failed: %s", str(e))
        sys.exit(1)


def run_classification(main_ledger: Path) -> None:
    """Run transaction classification steps.

    Args:
    ----
        main_ledger: Path to the main ledger file.

    """
    logger.info("\n=== TRANSACTION CLASSIFICATION ===")
    rules_file = Path("import/mercury/classification_rules.json")

    # 1. Rules-based classification
    logger.info("Running rules-based classification...")
    result = subprocess.run(
        [
            "python3",
            "bin/hledger-classify",
            str(main_ledger),
            str(rules_file),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        logger.error("Classification failed")
        logger.error(result.stderr)
        sys.exit(1)

    # 2. AI classification fallback (via MercuryImporter)
    logger.info("Running AI classification fallback...")
    result = subprocess.run(
        ["python3", "mercury_import.py", "--input-dir", "import/mercury/in"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        logger.error("AI classification failed")
        logger.error(result.stderr)
        sys.exit(1)


def validate_ledger(main_ledger: Path) -> None:
    """Validate ledger file format.

    Args:
    ----
        main_ledger: Path to the main ledger file.

    """
    logger.info("\n=== LEDGER VALIDATION ===")
    result = subprocess.run(
        ["python3", "test/ledger_format.py", str(main_ledger)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        logger.error("Ledger validation failed")
        logger.error(result.stderr)
        sys.exit(1)


def generate_reports(main_ledger: Path, reports_dir: Path) -> None:
    """Generate financial reports using hledger.

    Args:
    ----
        main_ledger: Path to the main ledger file.
        reports_dir: Path to the directory where reports will be saved.

    """
    logger.info("\n=== GENERATING REPORTS ===")
    reports_dir.mkdir(exist_ok=True)

    reports = [
        ("balancesheet", "balance_sheet"),
        ("incomestatement", "income_statement"),
        ("cashflow", "cash_flow"),
        ("balance --monthly", "monthly_summary"),
    ]

    for hledger_cmd, report_name in reports:
        logger.info("Generating %s report...", report_name.replace("_", " ").title())
        output_file = reports_dir / f"{report_name}.txt"
        cmd = ["hledger", "-f", str(main_ledger), *hledger_cmd.split()]
        try:
            with open(output_file, "w") as f:
                subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    check=True,
                    text=True,
                )
        except subprocess.CalledProcessError as e:
            logger.exception("Failed to generate %s report: %s", report_name, e.stderr)
            sys.exit(1)


def classification_verification(main_ledger: Path) -> None:
    """Interactive classification verification.

    Args:
    ----
        main_ledger: Path to the main ledger file.

    """
    logger.info("\n=== INTERACTIVE VERIFICATION ===")
    try:
        from bin.verify_classifications import ClassificationVerifier

        rules_path = Path("import/mercury/classification_rules.json")
        if not rules_path.exists():
            logger.error("Classification rules missing at %s", rules_path.resolve())
            return

        verifier = ClassificationVerifier(rules_path, main_ledger)
        verifier.main()

    except ImportError as e:
        logger.exception("Verification system unavailable: %s", str(e))
    except Exception as e:
        logger.exception("Verification failed: %s", str(e))


def main() -> None:
    """Main entry point of the script."""
    try:
        config = {
            "ledger_dir": Path.cwd(),
            "mercury_input_dir": Path("import/mercury/in"),
            "main_ledger": Path("complete_ledger.journal"),
            "reports_dir": Path("reports"),
        }

        system_checks()
        check_python_dependencies()

        # Add account generation
        logger.info("\n=== GENERATING ACCOUNTS ===")
        subprocess.run(
            [
                "python3",
                "scripts/generate_accounts.py",
                "import/mercury/classification_rules.json",
                "import/mercury/accounts.beancount",
            ],
            check=True,
        )

        # Process transactions FIRST
        process_transactions(config["mercury_input_dir"])

        # THEN check account declarations
        check_account_declarations(config["main_ledger"])

        run_repository_maintenance()
        run_classification(config["main_ledger"])
        validate_ledger(config["main_ledger"])
        generate_reports(config["reports_dir"])
        classification_verification(config["main_ledger"])

        logger.info("\n=== PIPELINE COMPLETE ===")
        logger.info("Reports available in: %s", config["reports_dir"].resolve())

    except Exception:
        logger.exception("Pipeline failed due to unexpected error")
        sys.exit(1)


if __name__ == "__main__":
    main()
