"""Database sync module.

This module handles syncing the local DuckDB database to the data lake.
"""

import os
import subprocess
from datetime import datetime
from pathlib import Path

# Paths
WORKSPACE_ROOT = Path(os.getenv('WORKSPACE_ROOT', '/Users/srvo/ethifinx'))
LOCAL_DB_PATH = WORKSPACE_ROOT / "data" / "research.duckdb"
LAKE_PATH = "/Users/srvo/lake/ethifinx/db"

def sync_to_lake():
    """Sync the local database to the data lake.
    
    Creates a timestamped backup and maintains the latest version.
    """
    # Ensure lake directory exists
    lake_dir = Path(LAKE_PATH)
    lake_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate paths
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = lake_dir / f"research_{timestamp}.duckdb"
    latest_path = lake_dir / "research_latest.duckdb"
    
    # Sync commands
    rsync_backup = [
        "rsync",
        "-av",  # archive mode, verbose
        "--checksum",  # skip based on checksum
        str(LOCAL_DB_PATH),
        str(backup_path)
    ]
    
    rsync_latest = [
        "rsync",
        "-av",  # archive mode, verbose
        "--checksum",  # skip based on checksum
        str(LOCAL_DB_PATH),
        str(latest_path)
    ]
    
    try:
        # Create timestamped backup
        print(f"\nCreating backup: {backup_path}")
        result = subprocess.run(rsync_backup, check=True, capture_output=True, text=True)
        print(result.stdout)
        
        # Update latest version
        print(f"\nUpdating latest: {latest_path}")
        result = subprocess.run(rsync_latest, check=True, capture_output=True, text=True)
        print(result.stdout)
        
        print("\nSync completed successfully")
        
    except subprocess.CalledProcessError as e:
        print(f"Error during sync: {str(e)}")
        print(f"Error output: {e.stderr}")
        raise

if __name__ == "__main__":
    sync_to_lake() 