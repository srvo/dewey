#!/usr/bin/env python3

"""Script to fix backtick issues in Python files.

This script:
1. Takes a list of files with backtick issues
2. Removes markdown-style backticks and code block syntax
3. Preserves the actual code content
"""

import os
import logging

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("backtick_fixer")

# List of files with known backtick issues
FILES_TO_FIX = [
    "src/dewey/core/config/config_handler.py",
    "src/dewey/core/config/logging.py",
    "src/dewey/core/crm/contact_consolidation.py",
    "src/dewey/core/crm/email_classifier/process_feedback.py",
    "src/dewey/core/crm/enrichment/attio_onyx_enrichment_engine.py",
    "src/dewey/core/db/data_handler.py",
    "src/dewey/core/engines/apitube.py",
    "src/dewey/core/engines/consolidated_gmail_api.py",
    "src/dewey/core/engines/duckduckgo_engine.py",
    "src/dewey/core/engines/fmp_engine.py",
    "src/dewey/core/engines/fred_engine.py",
    "src/dewey/core/engines/openfigi.py",
    "src/dewey/core/engines/polygon_engine.py",
    "src/dewey/core/engines/sec_engine.py",
    "src/dewey/core/engines/tavily.py",
    "src/dewey/core/engines/yahoo_finance_engine.py",
    "src/dewey/core/research/json_research_integration.py",
    "src/dewey/core/research/port/tic_delta_workflow.py",
    "src/dewey/core/research/port/tick_report.py",
    "src/dewey/core/research/utils/analysis_tagging_workflow.py",
    "src/dewey/core/research/utils/research_output_handler.py",
    "src/dewey/maintenance/consolidated_code_analyzer.py",
]


def fix_file(file_path: str) -> None:
    """Fix backtick issues in a Python file."""
    try:
        # Read the file
        with open(file_path, "r") as f:
            lines = f.readlines()

        # Remove markdown and code block syntax
        fixed_lines = []
        in_code_block = False
        skip_next = False

        for line in lines:
            # Skip empty lines at the start
            if not fixed_lines and not line.strip():
                continue

            # Skip markdown code block syntax
            if line.strip() in ("```", "```python"):
                in_code_block = not in_code_block
                continue

            # Skip refactor headers if present
            if not fixed_lines and line.strip().startswith("# Refactored from:"):
                skip_next = True
                continue

            if skip_next:
                if line.strip().startswith("# Date:") or line.strip().startswith(
                    "# Refactor Version:"
                ):
                    continue
                skip_next = False

            # Keep the actual code
            fixed_lines.append(line)

        # Write the fixed content back
        with open(file_path, "w") as f:
            f.writelines(fixed_lines)

        logger.info(f"Fixed {file_path}")

    except Exception as e:
        logger.error(f"Error fixing {file_path}: {str(e)}")


def main():
    """Main entry point."""
    logger.info("Starting backtick fixer")

    fixed_count = 0
    error_count = 0

    for file_path in FILES_TO_FIX:
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            continue

        try:
            fix_file(file_path)
            fixed_count += 1
        except Exception as e:
            logger.error(f"Failed to fix {file_path}: {str(e)}")
            error_count += 1

    logger.info(f"\nSummary:")
    logger.info(f"Fixed {fixed_count} files")
    logger.info(f"Failed to fix {error_count} files")


if __name__ == "__main__":
    main()
