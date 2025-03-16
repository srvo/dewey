from __future__ import annotations

from api_manager_flow import api_manager_flow
from prefect.deployments import Deployment
from prefect.server.schemas.schedules import CronSchedule


def create_deployment(
    flow: callable,
    name: str,
    version: str,
    work_queue_name: str,
    cron_schedule: str,
    tags: list[str],
    description: str,
) -> Deployment:
    """Builds a Prefect deployment from a given flow.

    Args:
    ----
        flow: The Prefect flow to deploy.
        name: The name of the deployment.
        version: The version of the deployment.
        work_queue_name: The name of the work queue.
        cron_schedule: A cron expression defining the schedule.
        tags: A list of tags to apply to the deployment.
        description: A description of the deployment.

    Returns:
    -------
        A Prefect Deployment object.

    """
    return Deployment.build_from_flow(
        flow=flow,
        name=name,
        version=version,
        work_queue_name=work_queue_name,
        schedule=CronSchedule(cron=cron_schedule),  # Run every 15 minutes
        tags=tags,
        description=description,
    )


def apply_deployment(deployment: Deployment) -> None:
    """Applies a Prefect deployment.

    Args:
    ----
        deployment: The Prefect Deployment object to apply.

    """
    deployment.apply()


if __name__ == "__main__":
    deployment = create_deployment(
        flow=api_manager_flow,
        name="api-manager-deployment",
        version="1",
        work_queue_name="default",
        cron_schedule="*/15 * * * *",
        tags=["api-manager", "monitoring"],
        description="Monitors API health, usage, and rate limits",
    )

    apply_deployment(deployment)
