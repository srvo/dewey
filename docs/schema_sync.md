# Bidirectional Schema Synchronization

This document explains the bidirectional schema synchronization feature added to the MotherDuck schema updater tool.

## Overview

The bidirectional schema sync ensures that:

1. SQLAlchemy models stay in sync with the MotherDuck database schema
2. The MotherDuck database schema stays in sync with schema definitions in your code

This two-way sync helps prevent drift between your code and database, reducing bugs and making development more efficient.

## How It Works

The schema updater now supports two main workflows:

### Database → Code (Original Functionality)

1. Extracts schema from MotherDuck database
2. Generates SQLAlchemy models
3. Updates `models.py` file
4. Formats the output with Black

### Code → Database (New Functionality)

1. Extracts schema definitions from your code (e.g., EMAIL_SCHEMA in email import scripts)
2. Compares with the database schema
3. Generates ALTER TABLE statements to add missing columns
4. Optionally executes those ALTER statements

## Using the Bidirectional Sync

### Direct Schema Updater

You can use the schema updater with new command-line arguments:

```bash
python3 src/dewey/core/db/schema_updater.py --sync_to_db --execute_alters
```

Options:
- `--sync_to_db`: Enable bidirectional sync (code → database)
- `--execute_alters`: Execute the ALTER statements (otherwise just prints them)
- `--force_imports`: Force adding imports even if they might already exist
- `--no_primary_key_workaround`: Disable adding virtual primary keys for tables without them

### Helper Script

A helper script is provided at `scripts/bidirectional_sync.py`:

```bash
python3 scripts/bidirectional_sync.py --execute
```

Options:
- `--execute`: Execute ALTER statements (otherwise just prints them)
- `--force-imports`: Force adding imports
- `--no-primary-key`: Disable adding virtual primary keys

## Schema Definition Format

Schema definitions in code should use the CREATE TABLE format:

```python
EMAIL_SCHEMA = '''
CREATE TABLE emails (
    msg_id VARCHAR PRIMARY KEY,
    from_address VARCHAR,
    to_address VARCHAR,
    subject VARCHAR,
    date TIMESTAMP,
    thread_id VARCHAR,
    body_text TEXT,
    body_html TEXT,
    status VARCHAR DEFAULT 'new'
)
'''
```

The schema updater will parse these definitions and compare them with the database schema.

## Best Practices

1. **Run sync regularly**: After changes to schema definitions in code or database
2. **Version control models.py**: Keep track of changes to SQLAlchemy models
3. **Review ALTER statements**: Check the generated ALTER statements before executing them
4. **Test in development**: Always test schema changes in development before production
5. **Use centralized schema definitions**: Define schemas in one place and reference them elsewhere

## Configuration

The schema updater uses the same configuration as before, reading from:
- Environment variables (MOTHERDUCK_TOKEN)
- Configuration file at `/Users/srvo/dewey/config/dewey.yaml` 