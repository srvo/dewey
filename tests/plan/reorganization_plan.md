# Test Directory Reorganization Plan

## Current Structure
The current test directory structure is disorganized with tests spread across multiple directories:
- `tests/core/`: Core module tests
- `tests/dewey/`: General tests
- `tests/ui/`: UI module tests
- `tests/config/`: Config module tests
- `tests/docs/`: Documentation tests

## New Structure
The new structure will organize tests by test type:

```
tests/
├── unit/                # Unit tests
│   ├── core/            # Core module unit tests
│   ├── llm/             # LLM module unit tests
│   ├── ui/              # UI module unit tests
│   ├── config/          # Config module unit tests
│   └── utils/           # Utils module unit tests
├── integration/         # Integration tests
├── functional/          # End-to-end functional tests
├── conftest.py          # Global test fixtures
└── README.md            # Documentation for tests
```

## Implementation Steps

1. ✅ Create the new directory structure
2. ✅ Move test files to their corresponding locations
3. ✅ Update import paths in test files
4. ✅ Create or update conftest.py files
5. ✅ Verify tests run correctly in the new structure
6. ✅ Create cleanup script to remove original directories
7. ⬜ Run cleanup script after confirming successful reorganization

## Cleanup Instructions

After verifying that all tests run correctly in the new structure:

1. Run the cleanup script: `./tests/plan/cleanup.sh`
2. The script will:
   - Create a backup of the original directories in a temporary location
   - Remove the original test directories after confirmation
   - Print a summary of the cleanup operation

The backup will be available for a limited time in case any issues are discovered after cleanup.

## Completed
- Created base directory structure ✅
- Created move_tests.py script to handle reorganization ✅
- Executed the script and verified test movement ✅
- Created cleanup script for final removal of old directories ✅ 