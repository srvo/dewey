"""Deploy controversy monitoring flows to Prefect."""

from controversy_detection import monitor_all_companies
from prefect.deployments import Deployment
from prefect.filesystems import GitHub
from prefect.server.schemas.schedules import CronSchedule


def main() -> None:
    # Create GitHub storage block if it doesn't exist
    github_block = GitHub(
        name="rawl",
        repository="https://github.com/srvo/rawl.git",
        reference="main",
        include_git_objects=False,
    )
    github_block.save("rawl", overwrite=True)

    # Create deployment
    deployment = Deployment.build_from_flow(
        flow=monitor_all_companies,
        name="daily-controversy-monitor",
        schedule=CronSchedule(cron="0 2 * * *", timezone="UTC"),
        work_queue_name="controversy-monitor",
        storage=github_block,
        path="prefect/flows/controversy_detection.py:monitor_all_companies",
    )

    # Apply deployment
    deployment.apply()


if __name__ == "__main__":
    main()
