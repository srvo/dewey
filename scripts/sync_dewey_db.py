#!/usr/bin/env python
"""
Sync data between local dewey.duckdb and MotherDuck.

This script is a simple wrapper around the dewey.core.db.sync_duckdb module.
It provides a convenient way to sync data between a local dewey.duckdb file
and a MotherDuck (cloud) database.

Examples
--------
# Sync both ways (from MotherDuck to local and local to MotherDuck)
python scripts/sync_dewey_db.py --direction both

# Sync from MotherDuck to local only
python scripts/sync_dewey_db.py --direction down

# Sync from local to MotherDuck only
python scripts/sync_dewey_db.py --direction up

# Sync specific tables
python scripts/sync_dewey_db.py --tables emails,email_analyses,email_feedback

# Exclude specific tables
python scripts/sync_dewey_db.py --exclude email_raw,email_attachments

# Monitor for changes and sync automatically
python scripts/sync_dewey_db.py --monitor --interval 300

"""

import sys
from pathlib import Path

# Make sure the project root is in the path
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dewey.core.db.cli_duckdb_sync import SyncDuckDBScript


def main():
    """Run the sync script."""
    script = SyncDuckDBScript()
    script.run()


if __name__ == "__main__":
    main()
