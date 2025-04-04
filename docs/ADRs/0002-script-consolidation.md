# ADR 0002: Script Consolidation Strategy

## Status
Proposed

## Context
The scripts directory has grown organically with:
- Duplicate functionality
- Overlapping operations
- Inconsistent implementations
- Redundant code

This leads to:
- Maintenance challenges
- Inconsistent behavior
- Difficulty in adding new features

## Decision
Consolidate scripts into logical groups with shared functionality:

1. **Database Operations**:
   - Move to DatabaseMaintenance class
   - Expose via CLI commands
   - Deprecate standalone scripts

2. **Code Maintenance**:
   - Create CodeFixer class in core/maintenance/
   - Consolidate fix_*.py scripts
   - Add CLI interface

3. **Import Operations**:
   - Create ImportManager class
   - Consolidate import_*.py and run_*_import.sh
   - Standardize interfaces

4. **Test/Validation**:
   - Create TestManager class
   - Consolidate test-related scripts
   - Add standardized reporting

## Consequences
### Positive
- Reduced code duplication
- Improved maintainability
- Consistent behavior
- Better documentation
- Easier to add new features

### Negative
- Initial refactoring effort
- Need to update existing workflows
- Potential backward compatibility issues

## Migration Plan
1. Refactor remaining database scripts
2. Implement CodeFixer class
3. Implement ImportManager class
4. Implement TestManager class
5. Update documentation
6. Phase out old scripts
7. Verify backward compatibility