"""Test patterns for Prefect flows demonstrating recommended testing approaches."""

import asyncio
import logging
from typing import Never
from unittest.mock import patch

import pytest
from prefect import flow, task
from prefect.testing.utilities import run_flow_with_ctx


# Example task for testing
@task(retries=3, retry_delay_seconds=60)
def process_data(data: dict, logger=None) -> dict:
    """Example task that processes data with error handling."""
    if logger is None:
        logger = logging.getLogger(__name__)

    logger.info("Starting data processing")
    try:
        result = {"processed": data["input"] * 2}
        logger.info(f"Processing complete: {result}")
        return result
    except Exception as e:
        logger.exception(f"Processing failed: {e}")
        raise


# Example flow for testing
@flow
def example_flow(input_data: dict):
    """Example flow that demonstrates testing patterns."""
    return process_data(input_data)


# Unit Tests - Using task.fn
def test_process_data_task(task_runner, mock_logger) -> None:
    """Test the process_data task in isolation using task.fn."""
    # Test successful execution
    input_data = {"input": 5}
    result = task_runner(process_data, input_data, logger=mock_logger)
    assert result == {"processed": 10}
    mock_logger.info.assert_any_call("Starting data processing")

    # Test error handling
    with pytest.raises(KeyError):
        task_runner(process_data, {}, logger=mock_logger)
    mock_logger.error.assert_called()


# Integration Tests - Using run_flow_with_ctx
def test_example_flow() -> None:
    """Test the entire flow execution."""
    input_data = {"input": 5}
    result = run_flow_with_ctx(example_flow, input_data)
    assert result == {"processed": 10}


# Error Handling Tests - Using task.fn for direct testing
def test_task_retries(task_runner, mock_logger) -> None:
    """Test task retry behavior."""

    @task(retries=2, retry_delay_seconds=0)
    def failing_task() -> Never:
        mock_logger.info("Attempting task")
        msg = "Simulated failure"
        raise ValueError(msg)

    with pytest.raises(ValueError):
        task_runner(failing_task)

    # Should have logged the attempt
    mock_logger.info.assert_called_with("Attempting task")


# Mocking External Dependencies
def test_flow_with_mocked_dependency() -> None:
    """Test flow with mocked external dependency."""

    @task
    def external_api_call():
        # In real code, this would call an external API
        return {"data": "real_data"}

    @flow
    def dependent_flow():
        return external_api_call()

    # Mock the external API call
    with patch("prefect.tasks.run_task", return_value={"data": "mocked_data"}):
        result = run_flow_with_ctx(dependent_flow)
        assert result == {"data": "mocked_data"}


# Logging Tests - Using disable_run_logger
def test_logging_configuration(task_runner, mock_logger) -> None:
    """Test logging configuration and output."""

    @task
    def logging_task(logger) -> bool:
        logger.info("Test message")
        logger.error("Test error")
        return True

    result = task_runner(logging_task, mock_logger)
    assert result is True
    mock_logger.info.assert_called_with("Test message")
    mock_logger.error.assert_called_with("Test error")


# Async Flow Tests - Using run_flow_with_ctx
def test_async_flow() -> None:
    """Test asynchronous flow execution."""

    @task
    async def async_task(x):
        await asyncio.sleep(0.1)  # Simulate async operation
        return x * 2

    @flow
    async def async_flow(x):
        return await async_task(x)

    result = run_flow_with_ctx(async_flow, 5)
    assert result == 10


# State Tests - Testing task states
def test_task_states(task_runner) -> None:
    """Test task state transitions."""

    @task(retries=1)
    def state_task(should_fail: bool) -> str:
        if should_fail:
            msg = "Task failed"
            raise ValueError(msg)
        return "Success"

    # Test successful state
    result = task_runner(state_task, False)
    assert result == "Success"

    # Test failed state
    with pytest.raises(ValueError):
        task_runner(state_task, True)


# Parameter Tests - Testing flow parameters
def test_flow_parameters() -> None:
    """Test flow parameter validation."""

    @flow
    def parameterized_flow(x: int, y: str = "default") -> str:
        return f"{y}: {x}"

    result = run_flow_with_ctx(parameterized_flow, 42)
    assert result == "default: 42"

    result = run_flow_with_ctx(parameterized_flow, 42, y="custom")
    assert result == "custom: 42"


# Environment Tests
def test_environment_configuration(test_env) -> None:
    """Test environment configuration."""
    assert "PREFECT_API_URL" in test_env
    assert "DATABASE_URL" in test_env
    assert test_env["PREFECT_API_URL"].startswith("http")
