# Dewey Scripts Directory

This directory contains all utility and operational scripts for the Dewey project, following the project's structure conventions outlined in [CONVENTIONS.md](../CONVENTIONS.md).

## Guidelines for Script Development

1. **All scripts should be placed in this directory** rather than at the project root or in src/dewey/maintenance
2. **Scripts should inherit from BaseScript** where appropriate to utilize standardized configuration, logging, and error handling
3. **Document your scripts** with clear docstrings and comments
4. **Maintain consistent naming conventions**:
   - Use snake_case for script names
   - Prefix database-related scripts with `db_`
   - Prefix import-related scripts with `import_`
   - Shell scripts should use `.sh` extension

## Script Categories

### Database Maintenance (CLI Commands)
Database operations are now available as CLI commands via `src/dewey/cli/db.py`:

```bash
python -m dewey.cli.db [COMMAND] [ARGS]
```

Available commands:
- `cleanup-tables` - Clean up specified tables
- `analyze-tables` - Analyze tables and display statistics
- `drop-jv-tables` - Drop JV-related tables
- `drop-other-tables` - Drop all tables except those specified
- `cleanup-files` - Clean up database files matching patterns

For help on any command:
```bash
python -m dewey.cli.db [COMMAND] --help
```

Legacy database scripts have been deprecated in favor of these standardized commands.

### Data Import
- `import_import_client_onboarding.py` - Imports client onboarding data
- `import_import_institutional_prospects.py` - Imports institutional prospect data
- `run_client_import.sh` - Shell script for client data import
- `run_client_onboarding_import.sh` - Shell script for client onboarding import
- `run_family_offices_import.sh` - Shell script for family office data import
- `run_institutional_import.sh` - Shell script for institutional data import

### Code Maintenance
- `analyze_architecture.py` - Analyzes project architecture
- `document_directory.py` - Documents directory structure
- `precommit_analyzer.py` - Analyzes precommit issues
- `code_uniqueness_analyzer.py` - Analyzes code duplication
- `fix_backtick_files.py` - Fixes backtick issues in files
- `fix_backticks.py` - Alternative script for fixing backtick issues
- `fix_common_issues.py` - Fixes common code issues
- `fix_docstrings.py` - Fixes docstring formatting

### System Operations
- `run_unified_processor.py` - Runs the unified data processor
- `run_gmail_sync.py` - Syncs Gmail data
- `run_email_processor.py` - Processes email data
- `schedule_db_sync.py` - Schedules database sync operations
- `direct_db_sync.py` - Performs direct database sync
- `sync_table.py` - Syncs specific database tables

### Development Tools
- `RF_docstring_agent.py` - Assists with docstring generation
- `generate_legacy_todos.py` - Generates TODOs from legacy code
- `prd_builder.py` - Builds product requirement documents
- `test_writer.py` - Assists with test writing
- `check_abstract_methods.py` - Verifies abstract method implementation
- `log_cleanup.py` - Cleans up log files

### Utilities
- `cleanup_logs.sh` - Shell script for log cleanup
- `consolidate_logs.sh` - Shell script for log consolidation
- `lint_and_fix.sh` - Shell script for linting and fixing code issues
- `reorganize_legacy.sh` - Shell script for reorganizing legacy code
- `reorganize_tests.sh` - Shell script for reorganizing tests
- `test_fix_cycle.sh` - Shell script for test-fix cycle

## Usage

Most Python scripts can be run using:

```bash
python scripts/script_name.py [args]
```

Shell scripts can be run using:

```bash
./scripts/script_name.sh [args]
```

For detailed usage instructions for each script, run:

```bash
python scripts/script_name.py --help
```

## Adding New Scripts

When adding new scripts to this directory:

1. Follow the naming conventions above
2. Inherit from `BaseScript` where appropriate
3. Document the script in this README.md
4. Add appropriate error handling and logging
5. Make sure the script is executable (add shebang line and executable permissions for shell scripts)
