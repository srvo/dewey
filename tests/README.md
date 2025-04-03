# Dewey Test Organization

This directory contains tests for the Dewey application. Tests are organized into two main categories:

## Test Categories

### Unit Tests (`tests/unit/`)
Unit tests verify that individual components work correctly in isolation. These tests:
- Focus on a single function, class, or module
- Mock all external dependencies
- Run quickly without external resources
- Should be run frequently during development

Subdirectories:
- `db/`: Database component unit tests
- `llm/`: Language model component unit tests
- `ui/`: User interface component unit tests
- `bookkeeping/`: Bookkeeping functionality unit tests

### Integration Tests (`tests/integration/`)
Integration tests verify that multiple components work correctly together. These tests:
- Test interactions between components
- May require external resources (databases, APIs, etc.)
- Run more slowly than unit tests
- Should be run before deployments

Subdirectories:
- `db/`: Database integration tests (may require a real database)
- `llm/`: Language model integration tests (may call real LLM APIs)
- `ui/`: User interface integration tests

## Running Tests

Use pytest via uv to run tests following project conventions:

```bash
# Run all tests
uv run pytest

# Run all unit tests
uv run pytest tests/unit

# Run all integration tests
uv run pytest tests/integration

# Run specific test category
uv run pytest tests/unit/db
uv run pytest tests/unit/llm
uv run pytest tests/unit/ui
uv run pytest tests/unit/bookkeeping

# Run integration tests by category
uv run pytest tests/integration/db
uv run pytest tests/integration/llm
uv run pytest tests/integration/ui

# Run tests with specific markers
uv run pytest -m unit
uv run pytest -m "unit and db"
uv run pytest -m "integration and not slow"

# Run a specific test file
uv run pytest tests/unit/db/test_operations.py

# Run a specific test function
uv run pytest tests/unit/db/test_operations.py::test_function_name
```

## Test Fixtures

Common test fixtures are defined in `tests/conftest.py` and are available to all tests.
Component-specific fixtures may be defined in `conftest.py` files within the component directories.

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
