# ADR 0001: Database Operations Refactoring

## Status
Proposed

## Context
The project has accumulated numerous database-related scripts with duplicated logic for:
- Table cleanup
- Table analysis
- Data migration
- Schema management

This leads to:
- Maintenance overhead
- Inconsistent behavior
- Difficulty in adding new database operations

## Decision
Refactor database operations into:
1. A shared `DatabaseMaintenance` class in `src/dewey/core/db/operations.py`
2. Standardized CLI commands in `src/dewey/cli/db.py`
3. Updated scripts that leverage the shared functionality

Key changes:
- Centralized database connection handling
- Consistent logging and error handling
- Standardized CLI interface using Typer
- Shared configuration management

## Consequences
### Positive
- Reduced code duplication
- Improved maintainability
- Consistent behavior across operations
- Easier to add new database operations
- Better documentation and discoverability

### Negative
- Requires updating existing scripts
- Need to maintain backward compatibility
- Initial refactoring effort

## Migration Steps
1. Update existing scripts to use new shared functionality
2. Deprecate old script versions
3. Update documentation
4. Verify backward compatibility