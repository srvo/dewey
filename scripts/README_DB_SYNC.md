# DuckDB Sync Functionality

This directory contains scripts for synchronizing data between a local DuckDB instance and MotherDuck (cloud).

## Overview

The sync functionality supports two main modes:

1. **Full Sync**: Copies all data from MotherDuck to the local database
2. **Incremental Sync**: Only syncs data that has changed since the last sync

Additionally, the system:
- Automatically tracks table modifications in the local database
- Automatically syncs on write operations (when you modify local data)
- Can be scheduled to run daily full syncs at night

## Scripts

### 1. `direct_db_sync.py`

The main sync script that performs the synchronization between MotherDuck and local DuckDB.

Usage:
```
python scripts/direct_db_sync.py [--table TABLE_NAME] [--mode {full,incremental}] [--verbose]
```

Options:
- `--table TABLE_NAME`: Sync only the specified table
- `--mode {full,incremental}`: Sync mode (default: full)
- `--verbose`: Enable verbose logging

Examples:
```
# Sync all tables (full sync)
python scripts/direct_db_sync.py

# Sync only the 'emails' table
python scripts/direct_db_sync.py --table emails

# Incremental sync of all tables
python scripts/direct_db_sync.py --mode incremental
```

### 2. `schedule_db_sync.py`

Sets up a scheduled job to run a full database sync at a specified time.

Usage:
```
python scripts/schedule_db_sync.py [--hour HOUR] [--minute MINUTE] [--remove]
```

Options:
- `--hour HOUR`: Hour to run the sync (24-hour format, default: 3)
- `--minute MINUTE`: Minute to run the sync (default: 0)
- `--remove`: Remove the scheduled job instead of adding it

Examples:
```
# Schedule daily sync at 3:00 AM (default)
python scripts/schedule_db_sync.py

# Schedule daily sync at 2:30 AM
python scripts/schedule_db_sync.py --hour 2 --minute 30

# Remove the scheduled sync job
python scripts/schedule_db_sync.py --remove
```

## Recommended Setup

1. **Regular Use:**
   - The system automatically syncs modified tables when you write to the local database
   - This ensures your changes are pushed to MotherDuck

2. **Daily Full Sync:**
   - Schedule a daily full sync to run at night
   - This ensures complete consistency between local and cloud databases
   - Set up with: `python scripts/schedule_db_sync.py`

3. **Before Important Operations:**
   - Run a full sync before critical operations to ensure you have the latest data
   - `python scripts/direct_db_sync.py`

## Troubleshooting

1. **Sync Errors:**
   - Check logs in the `logs/` directory
   - Retry with `--verbose` flag for more detailed logging

2. **Connection Issues:**
   - Ensure the `MOTHERDUCK_TOKEN` environment variable is set
   - Check network connectivity to MotherDuck

3. **Column Mapping Issues:**
   - The system includes special handling for known column name mismatches
   - For new cases, edit `direct_db_sync.py` to add mappings

## Notes

- Full syncs can be time-consuming for large databases
- Incremental syncs are much faster but rely on updated timestamps
- The sync metadata is stored in the `dewey_sync_metadata` table in your local database
