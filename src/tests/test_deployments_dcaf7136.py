"""Tests for Prefect deployment configuration."""

from datetime import timedelta

from prefect import flow
from prefect.deployments import Deployment
from prefect.server.schemas.schedules import IntervalSchedule


@flow
def test_flow() -> str:
    """Test flow that returns a value."""
    return "test"


def test_flow_deployment() -> None:
    """Test that flow deployment uses the correct API."""
    # Create a deployment
    deployment = Deployment.build_from_flow(
        flow=test_flow,
        name="test-deployment",
        schedule=IntervalSchedule(interval=timedelta(hours=1)),
        tags=["test"],
        description="Test deployment",
        work_queue_name="test-queue",
    )

    # Verify deployment attributes
    assert deployment.name == "test-deployment"
    assert deployment.tags == ["test"]
    assert deployment.description == "Test deployment"
    assert deployment.schedule.interval == timedelta(hours=1)
    assert deployment.work_queue_name == "test-queue"


def test_flow_run() -> None:
    """Test that flow can be run directly."""
    result = test_flow()
    assert result == "test"
