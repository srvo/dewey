#!/usr/bin/env python3
import fnmatch
import json
import logging
import re
import shutil
from pathlib import Path

# Rule sources in priority order (lower numbers = higher priority)
RULE_SOURCES = [
    ("overrides.json", 0),  # Highest priority
    ("manual_rules.json", 1),
    ("base_rules.json", 2),  # Lowest priority
]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Use absolute path for classification rules file
CLASSIFICATION_FILE = Path.home() / "books/import/mercury/classification_rules.json"
LEDGER_FILE = Path.home() / ".hledger.journal"
BACKUP_EXT = ".bak"


def format_category(category_str: str) -> str:
    """Convert category string to proper Ledger format (PascalCase).

    Args:
    ----
        category_str: The category string to format.

    Returns:
    -------
        The formatted category string.

    """
    parts = category_str.split(":")
    formatted_parts = [part.title().replace(" ", "") for part in parts]
    return ":".join(formatted_parts)


def load_prioritized_rules() -> list[tuple[tuple[str, dict], int]]:
    """Load rules from multiple sources with priority.

    Returns
    -------
        A list of rules with their priority, sorted by priority and pattern specificity.

    """
    all_rules = []
    base_dir = Path(__file__).parent.parent / "rules"

    for filename, priority in RULE_SOURCES:
        file_path = base_dir / filename
        if file_path.exists():
            with open(file_path) as f:
                rules = json.load(f)
                all_rules.extend((rule, priority) for rule in rules["patterns"].items())

    # Sort by priority then pattern specificity
    return sorted(
        all_rules,
        key=lambda x: (
            x[1],  # Priority level first
            -len(x[0][0]),  # Longer patterns get priority
        ),
    )


def compile_pattern(pattern: str) -> re.Pattern:
    """Compile a pattern into a regex object.

    Args:
    ----
        pattern: The pattern string to compile.

    Returns:
    -------
        A compiled regex pattern.

    """
    if pattern.startswith("^") or pattern.endswith("$"):
        logger.debug(f"Compiling regex pattern: {pattern}")
        compiled = re.compile(pattern)
    else:
        translated = fnmatch.translate(f"*{pattern}*")
        compiled = re.compile(translated, re.IGNORECASE)
    return compiled


def load_classification_rules() -> list[tuple[re.Pattern, str, int]]:
    # Loads classification rules from prioritized sources
    """Load and compile classification rules with priority.

    Returns
    -------
        A list of compiled rules with their associated category and priority.

    """
    logger.info("Loading classification rules with priority system")

    rules = load_prioritized_rules()
    compiled_rules = []

    for (pattern, data), priority in rules:
        category = data["category"]
        formatted_category = format_category(category)

        # Handle different pattern types
        compiled = compile_pattern(pattern)

        compiled_rules.append((compiled, formatted_category, priority))

    logger.info(f"Loaded {len(compiled_rules)} classification rules")
    return compiled_rules


def parse_journal_entries(file_path: Path) -> list[dict]:
    """Parse hledger journal file into structured transactions.

    Args:
    ----
        file_path: The path to the hledger journal file.

    Returns:
    -------
        A list of structured transactions.

    """
    logger.info(f"Parsing journal file: {file_path}")

    with open(file_path) as f:
        content = f.read()

    transactions = []
    current_tx = {"postings": []}

    for line in content.split("\n"):
        line = line.rstrip()
        if not line:
            if current_tx.get("postings"):
                transactions.append(current_tx)
                current_tx = {"postings": []}
            continue

        if not current_tx.get("date"):
            # Transaction header line
            date_match = re.match(r"^(\d{4}-\d{2}-\d{2})(\s+.*?)$", line)
            if date_match:
                current_tx["date"] = date_match.group(1)
                current_tx["description"] = date_match.group(2).strip()
            continue

        # Parse posting lines
        if line.startswith("    "):
            parts = re.split(r"\s{2,}", line.strip(), 1)
            account = parts[0].strip()
            amount = parts[1].strip() if len(parts) > 1 else ""
            current_tx["postings"].append({"account": account, "amount": amount})

    if current_tx.get("postings"):
        transactions.append(current_tx)

    logger.info(f"Found {len(transactions)} transactions")
    return transactions


def process_transactions(
    transactions: list[dict],
    rules: list[tuple[re.Pattern, str, int]],
) -> list[dict]:
    """Apply classification rules to journal entries.

    Args:
    ----
        transactions: A list of transactions to process.
        rules: A list of classification rules.

    Returns:
    -------
        A list of updated transactions.

    """
    updated_count = 0

    for tx in transactions:
        description = tx["description"]
        original_account = tx["postings"][0]["account"] if tx["postings"] else ""

        # Find matching rules in priority order
        for pattern, category, _ in rules:
            if pattern.search(description):
                if original_account != category:
                    tx["postings"][0]["account"] = category
                    updated_count += 1
                    logger.debug(
                        f"Updated transaction '{description[:30]}...' from {original_account} to {category}",
                    )
                break  # Use first match

    logger.info(f"Updated {updated_count} transaction classifications")
    return transactions


def serialize_transactions(transactions: list[dict]) -> str:
    """Convert structured transactions back to journal format.

    Args:
    ----
        transactions: A list of structured transactions.

    Returns:
    -------
        A string representation of the transactions in journal format.

    """
    journal_lines = []

    for tx in transactions:
        header = f"{tx['date']} {tx['description']}"
        journal_lines.append(header)

        for posting in tx["postings"]:
            line = f"    {posting['account']}"
            if posting["amount"]:
                line += f"  {posting['amount']}"
            journal_lines.append(line)

        journal_lines.append("")  # Empty line between transactions

    return "\n".join(journal_lines).strip() + "\n"


def write_journal_file(content: str, file_path: Path) -> None:
    """Write updated journal file with backup.

    Args:
    ----
        content: The content to write to the journal file.
        file_path: The path to the journal file.

    """
    backup_path = file_path.with_suffix(f".{BACKUP_EXT}")

    try:
        # Create backup
        logger.info(f"Creating backup at {backup_path}")
        shutil.copy2(file_path, backup_path)

        # Write new content
        logger.info(f"Writing updated journal to {file_path}")
        with open(file_path, "w") as f:
            f.write(content)

    except Exception as e:
        logger.exception(f"Failed to write journal file: {e!s}")
        if backup_path.exists():
            logger.info("Restoring from backup")
            shutil.move(backup_path, file_path)
        raise


def main() -> None:
    """Main processing workflow."""
    try:
        # Load configuration
        rules = load_classification_rules()

        # Process journal entries
        transactions = parse_journal_entries(LEDGER_FILE)
        updated_transactions = process_transactions(transactions, rules)
        new_content = serialize_transactions(updated_transactions)

        # Write results
        write_journal_file(new_content, LEDGER_FILE)
        logger.info("Successfully updated journal entries")

    except Exception as e:
        logger.exception(f"Failed to process journal: {e!s}")
        raise


if __name__ == "__main__":
    main()
