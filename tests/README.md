# Dewey Tests

This directory contains tests for the Dewey project.

## Directory Structure

The tests are organized into the following categories:

- `unit/`: Unit tests for individual components
  - `core/`: Tests for the core module
  - `llm/`: Tests for the LLM module
  - `ui/`: Tests for the UI module
  - `config/`: Tests for the config module
  - `utils/`: Tests for the utils module
- `integration/`: Integration tests that verify how components work together
- `functional/`: End-to-end functional tests that verify overall system behavior

Each module's tests mirror the source code organization to make it easy to find tests for specific components.

## Running Tests

To run all tests:

```bash
python -m pytest
```

To run a specific test module:

```bash
python -m pytest tests/unit/core/db
```

To run tests with coverage:

```bash
python -m pytest --cov=src/dewey
```

## Writing Tests

When adding new tests, follow these guidelines:

1. Place tests in the appropriate category (unit, integration, functional)
2. Mirror the source code structure within that category
3. Name test files with a `test_` prefix
4. Name test functions with a `test_` prefix
5. Include docstrings that describe what the test is verifying
6. Use fixtures from `conftest.py` when appropriate

## Test Fixtures

Common test fixtures are defined in `conftest.py` files at various levels:
- Top-level fixtures in `/tests/conftest.py`
- Module-specific fixtures in e.g. `/tests/unit/core/conftest.py`

## Test Coverage

Aim for high test coverage of new code. The project's coverage goals are:
- Unit tests: 90% or higher
- Integration tests: Cover all critical paths
- Functional tests: Cover main user workflows 