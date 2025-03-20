"""Tests for Prefect flow serving configuration."""

import pytest
from prefect import flow
from prefect.server.schemas.schedules import CronSchedule


@flow
def test_flow() -> str:
    """Test flow that returns a value."""
    return "test"


def test_flow_serve() -> None:
    """Test that flow serving uses the correct API."""
    # Create a deployment using serve
    deployment = test_flow.serve(
        name="test-deployment",
        work_pool_name="test-pool",
        schedule=(CronSchedule(cron="0 2 * * *", timezone="UTC")),
        tags=["test"],
        description="Test deployment",
    )

    # Verify deployment attributes
    assert deployment.name == "test-deployment"
    assert deployment.work_pool_name == "test-pool"
    assert deployment.tags == ["test"]
    assert deployment.description == "Test deployment"

    # Verify schedule
    assert deployment.schedule.cron == "0 2 * * *"
    assert deployment.schedule.timezone == "UTC"


@pytest.mark.asyncio
async def test_flow_run() -> None:
    """Test that flow can be run directly."""
    result = await test_flow()
    assert result == "test"
