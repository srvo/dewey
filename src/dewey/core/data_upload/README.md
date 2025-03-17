# Data Upload to MotherDuck

This directory contains scripts for uploading data from various sources to MotherDuck.

## Overview

The upload process supports the following file types:
- DuckDB files (.duckdb)
- SQLite files (.sqlite, .db)
- CSV files (.csv)
- JSON files (.json)
- Parquet files (.parquet)

## Scripts

### upload.py

This script uploads a single file to MotherDuck.

```bash
python upload.py --file /path/to/file.duckdb --target_db dewey --dedup_strategy replace
```

Options:
- `--file`: Path to the file to upload
- `--input_dir`: Directory containing input files (used with --file_pattern)
- `--file_pattern`: File pattern to match (e.g., *.duckdb)
- `--target_db`: Target MotherDuck database (default: dewey)
- `--dedup_strategy`: Strategy for handling duplicate tables (update, replace, skip, version)
- `--timeout_ms`: Timeout in milliseconds for database operations
- `--max_retries`: Maximum number of retries for failed uploads
- `--retry_delay`: Delay in seconds between retries
- `--verbose`: Enable verbose output

### batch_upload.py

This script uploads multiple files in batches.

```bash
python batch_upload.py --file_types duckdb,csv --dedup_strategy replace --batch_size 5 --max_files 20 --input_dir /path/to/data --exclude_dirs dir1,dir2
```

Options:
- `--input_dir`: Directory containing files to upload (default: /Users/srvo/input_data)
- `--target_db`: Target MotherDuck database (default: dewey)
- `--dedup_strategy`: Strategy for handling duplicate tables (update, replace, skip, version)
- `--batch_size`: Number of files to process in each batch (default: 5)
- `--file_types`: Comma-separated list of file types to process (default: duckdb,sqlite,csv,json,parquet)
- `--max_files`: Maximum number of files to process per file type
- `--verbose`: Enable verbose logging
- `--exclude_dirs`: Comma-separated list of directories to exclude

### upload_port_direct.py

This script directly uploads the port.duckdb file to MotherDuck.

```bash
python upload_port_direct.py
```

### check_data.py

This script checks the data in the MotherDuck database.

```bash
python check_data.py --prefix input_data_ --list_only
python check_data.py --table input_data_blog_signup_form_responses
```

Options:
- `--database`: MotherDuck database name (default: dewey)
- `--prefix`: Filter tables by prefix
- `--table`: Specific table to check
- `--list_only`: Only list tables, don't show details
- `--verbose`: Enable verbose logging

## Deduplication Strategies

- `update`: Update existing tables with new data
- `replace`: Drop and recreate tables
- `skip`: Skip tables that already exist
- `version`: Create a new version of the table with a timestamp suffix

## Table Naming Convention

Tables are named based on the source file and table name:
- DuckDB/SQLite tables: `{source_file_prefix}_{table_name}`
- CSV/JSON/Parquet files: `{source_file_prefix}_{file_name}`

## Current Database Status

As of the latest upload, the MotherDuck database contains:
- Total tables: 72
- Tables by prefix:
  - input_data_: 34 tables
  - activedata_: 6 tables
  - raw_: 9 tables
  - port_: 6 tables

## Troubleshooting

### Permission Issues

If you encounter permission issues with files, try:
- Checking file ownership: `ls -la /path/to/files/`
- Changing file permissions: `chmod +r /path/to/file`

### Complex Schema Issues

For files with complex schemas, use the direct upload approach:
```bash
python upload.py --file /path/to/file.duckdb --target_db dewey --dedup_strategy replace
```

### Table Name Conflicts

If you encounter table name conflicts, try using a different deduplication strategy:
```bash
python upload.py --file /path/to/file.duckdb --target_db dewey --dedup_strategy version
``` 