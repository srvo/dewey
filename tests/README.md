# Dewey Tests

This directory contains the test suite for the Dewey project. The test structure follows the guidelines specified in [CONVENTIONS.md](../CONVENTIONS.md).

## Directory Structure

```
tests/
├── conftest.py          # Global test fixtures and configuration
├── helpers.py           # Helper functions for tests
├── unit/                # Unit tests for individual components
│   ├── core/            # Tests for core functionality
│   │   ├── db/          # Tests for database components
│   │   ├── utils/       # Tests for utility functions
│   │   ├── bookkeeping/ # Tests for bookkeeping components
│   │   └── ...          # Other core component tests
│   ├── llm/             # Tests for LLM components
│   └── ui/              # Tests for UI components
└── integration/         # Tests for component interactions
    ├── db/              # Database integration tests
    ├── llm/             # LLM integration tests
    ├── ui/              # UI integration tests
    └── ...              # Other integration tests
```

## Test Types

### Unit Tests

Unit tests focus on testing individual components in isolation. They should:

- Mock external dependencies (including other components)
- Test a single function, method, or class
- Be fast and focused
- Not require external services or databases

### Integration Tests

Integration tests focus on how components work together. They:

- Test interactions between multiple components
- May require more complex setup
- Often mock external services but test real component interactions
- Verify that components work together correctly

## Running Tests

Tests can be run using:

```bash
uv run pytest tests/unit               # Run all unit tests
uv run pytest tests/integration        # Run all integration tests
uv run pytest tests/unit/core/db       # Run specific test directory
uv run pytest tests/unit/core/db/test_utils.py::test_function  # Run specific test
```

## Test Fixtures

Common test fixtures are defined in `conftest.py` files:

- Root `conftest.py`: Global fixtures for all tests
- Directory-specific `conftest.py`: Fixtures for specific test categories

Use fixtures to avoid duplicating setup code and to ensure consistent test environments.

## Test Helpers

The `helpers.py` file contains utility functions for tests. Use these to simplify common testing tasks.

## Best Practices

1. **Mirror the source structure**: Tests should mirror the structure of the code they're testing.
2. **Use descriptive names**: Test names should clearly indicate what they're testing.
3. **One assertion per test**: Generally, focus each test on a single behavior.
4. **Use fixtures**: Leverage pytest fixtures for common setup.
5. **Mock external dependencies**: Use unittest.mock to isolate components during testing.
6. **Test edge cases**: Include tests for error conditions and boundary cases.
7. **Keep tests independent**: Tests should not rely on the results of other tests.

## Legacy Tests

Tests previously in the `prod/` directory have been reorganized into the `unit/` and `integration/` directories according to their function. New tests should be added to the appropriate directory following this structure.
