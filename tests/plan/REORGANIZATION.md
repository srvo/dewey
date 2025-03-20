# Tests Directory Reorganization Plan

## Current Issues
- Duplication: both `tests/core` and `tests/dewey/core` directories
- Inconsistent structure compared to the source code
- Top-level test files that should be organized into modules
- Multiple conftest.py files in different locations

## Proposed Structure
```
tests/
├── conftest.py                # Top-level test configuration
├── __init__.py                # Make tests importable
├── unit/                      # Unit tests for all modules
│   ├── __init__.py
│   ├── core/                  # Tests for core module
│   │   ├── __init__.py
│   │   ├── db/
│   │   ├── crm/
│   │   └── bookkeeping/
│   ├── llm/                   # Tests for llm module
│   │   ├── __init__.py
│   │   └── api_clients/
│   ├── ui/                    # Tests for ui module
│   │   ├── __init__.py
│   │   └── components/
│   ├── config/                # Tests for config module
│   │   └── __init__.py
│   └── utils/                 # Tests for utils module
│       └── __init__.py
├── integration/               # Integration tests
│   ├── __init__.py
│   └── test_script_integration.py
├── functional/                # Functional/e2e tests
│   └── __init__.py
└── helpers.py                 # Shared test helpers
```

## Migration Steps
1. Create the new directory structure
2. Move existing test files to appropriate directories
   - Move tests from `tests/core` to `tests/unit/core`
   - Move tests from `tests/dewey/core` to `tests/unit/core`
   - Move tests from `tests/dewey/llm` to `tests/unit/llm`
   - Move other tests to their corresponding unit test directories
3. Consolidate conftest.py files
4. Update imports in test files where needed
5. Ensure test discovery still works

## Benefits
- Clear separation between unit, integration, and functional tests
- Structure mirrors the source code organization
- Easier to find tests for a specific module
- Less confusion about where to add new tests
- Consistent with Dewey conventions 