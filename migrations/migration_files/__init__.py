"""Migration files for the Dewey project.

This package contains database migration files that define the schema and
structure of the database. Each migration file follows the format:
    YYYYMMDD_HHMMSS_migration_name.py

Migration files must contain:
- migrate(conn): Function to apply the migration
- rollback(conn): Function to roll back the migration (optional but recommended)
"""
