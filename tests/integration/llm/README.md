# LiteLLM Test Suite

This directory contains the test suite for the LiteLLM implementation in the Dewey project.

## Overview

The test suite covers:

- `LiteLLMClient` class for interacting with various LLM providers
- Utility functions for working with LiteLLM
- Exception classes for handling errors
- Integration tests showing how components work together

## Test Files

- `test_litellm_client.py`: Tests for the `LiteLLMClient` class
- `test_litellm_utils.py`: Tests for utility functions
- `test_exceptions.py`: Tests for exception classes
- `test_litellm_integration.py`: Integration tests for the LiteLLM implementation
- `test_litellm_suite.py`: Test suite runner

## Running Tests

### Running Individual Test Files

```bash
# Run a specific test file
python -m unittest tests/prod/llm/test_litellm_client.py

# Run a specific test class
python -m unittest tests.prod.llm.test_litellm_client.TestLiteLLMClient

# Run a specific test method
python -m unittest tests.prod.llm.test_litellm_client.TestLiteLLMClient.test_init_with_config
```

### Running All LiteLLM Tests

```bash
# Run the test suite
python tests/prod/llm/test_litellm_suite.py

# Or use pytest
python -m pytest tests/prod/llm
```

## Test Coverage

The test suite provides coverage for:

1. **Configuration Loading**:
   - From environment variables
   - From Dewey config file
   - From Aider configuration
   - With explicit config object

2. **API Interactions**:
   - Text completions
   - Chat completions
   - Embeddings
   - Function calling
   - Model information

3. **Error Handling**:
   - Authentication errors
   - Rate limits
   - Timeouts
   - Connection issues
   - Invalid responses

4. **Utility Functions**:
   - Key management
   - Response parsing
   - Fallback configuration
   - Azure setup

## Adding Tests

When adding new functionality to the LiteLLM implementation, please add corresponding tests:

1. Unit tests for new classes or functions
2. Integration tests for how they work with other components
3. Error handling tests for edge cases

## Running with Real API Keys

Some tests in `test_litellm_integration.py` are designed to test against real API endpoints but are skipped by default using `@pytest.mark.skip`.

To run these tests:

1. Remove the `@pytest.mark.skip` decorator
2. Set valid API keys in your environment
3. Run the specific test file

```bash
export OPENAI_API_KEY=your_actual_key
python -m unittest tests/prod/llm/test_litellm_integration.py
```

**Important**: Never commit real API keys to the test files.
