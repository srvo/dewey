#!/usr/bin/env python3
"""
Bidirectional Schema Sync Script.

This script demonstrates how to use the bidirectional schema sync functionality
to keep your database schema and code models in sync.

Usage:
python3 bidirectional_sync.py --help
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent
sys.path.append(str(project_root))

from src.dewey.core.db.schema_updater import main as update_schema


def run_bidirectional_sync(
    execute_alters=False, force_imports=False, add_primary_key=True,
):
    """Run the bidirectional schema sync process."""
    print("Starting bidirectional schema sync...")
    print(f"Execute ALTER statements: {execute_alters}")

    # Call the schema updater main function with sync_to_db=True
    return update_schema(
        force_imports=force_imports,
        add_primary_key_if_missing=add_primary_key,
        sync_to_db=True,
        execute_alters=execute_alters,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run bidirectional schema synchronization.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute ALTER statements to update database schema",
    )
    parser.add_argument(
        "--force-imports",
        action="store_true",
        help="Force adding imports even if they might already exist",
    )
    parser.add_argument(
        "--no-primary-key",
        action="store_false",
        dest="add_primary_key",
        help="Disable adding virtual primary keys for tables without them",
    )

    args = parser.parse_args()

    sys.exit(
        run_bidirectional_sync(
            execute_alters=args.execute,
            force_imports=args.force_imports,
            add_primary_key=args.add_primary_key,
        ),
    )
