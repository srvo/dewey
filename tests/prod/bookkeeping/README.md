# Bookkeeping Module Tests

This directory contains unit tests for the Dewey bookkeeping module components.

## Test Coverage

The tests cover the following modules:

1. **Account Validator** (`test_account_validator.py`): Tests the `AccountValidator` class that validates ledger accounts against a set of rules.
2. **Transaction Categorizer** (`test_transaction_categorizer.py`): Tests the `JournalCategorizer` class that categorizes transactions in journal files.
3. **Duplicate Checker** (`test_duplicate_checker.py`): Tests the `DuplicateChecker` class that identifies duplicate ledger files.
4. **HLedger Utils** (`test_hledger_utils.py`): Tests the `HledgerUpdater` class that updates opening balances in journal files.

## Running Tests

To run all bookkeeping tests:

```bash
python -m pytest tests/prod/bookkeeping
```

To run a specific test file:

```bash
python -m pytest tests/prod/bookkeeping/test_account_validator.py
```

To run a specific test:

```bash
python -m pytest tests/prod/bookkeeping/test_account_validator.py::TestAccountValidator::test_init
```

## Test Structure

The tests use pytest fixtures and mocks to isolate components and avoid external dependencies:

- `conftest.py`: Contains common fixtures used across multiple test files
- Each test module contains mocks for file system operations and external commands
- Tests avoid relying on actual file system or command execution

## Common Testing Patterns

1. **Interface Testing**: Verifying components properly implement interfaces
2. **Error Handling**: Testing how components handle various error conditions
3. **Command Execution**: Mocking subprocess calls to test command-line tools
4. **File Operations**: Mocking file system operations to test without actual files
5. **Configuration Handling**: Testing with various configuration options

## Adding New Tests

When adding new tests:

1. Follow the existing patterns for mocking dependencies
2. Use the fixtures in `conftest.py` where appropriate
3. Ensure tests are isolated and do not depend on external state
4. Add appropriate assertions to verify expected behavior
