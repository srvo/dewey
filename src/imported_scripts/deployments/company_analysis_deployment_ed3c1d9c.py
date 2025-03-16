import os

from company_analysis import analyze_companies
from prefect.deployments import Deployment
from prefect.filesystems import LocalFileSystem
from prefect.infrastructure import Process
from prefect.server.schemas.schedules import CronSchedule

if __name__ == "__main__":
    # Get auth credentials from environment
    prefect_user = os.getenv("PREFECT_AUTH_USER", "srvo")
    prefect_pass = os.getenv("BASIC_AUTH_PASSWORD", "")

    # Construct API URL with basic auth if credentials are available
    api_url = "https://flow.sloane-collective.com/api"
    if prefect_user and prefect_pass:
        api_url = (
            f"https://{prefect_user}:{prefect_pass}@flow.sloane-collective.com/api"
        )

    # Create a local storage block for our flow code
    storage = LocalFileSystem(
        basepath="/var/lib/dokku/data/storage/prefect/flows",
        persist_local=True,
    )

    # Use Process infrastructure (since we're running on the same machine)
    infrastructure = Process(env={"PREFECT_API_URL": api_url})

    # Create the deployment
    deployment = Deployment.build_from_flow(
        flow=analyze_companies,
        name="company-analysis",
        version="1",
        work_queue_name="default",
        storage=storage,
        infrastructure=infrastructure,
        path="company_analysis.py",
        description="Analyzes companies for controversies using LLM models",
        parameters={
            "config_path": "/var/lib/dokku/data/storage/prefect/configs/latest_config.json",
        },
        tags=["company-analysis", "llm", "production"],
        schedule=(
            CronSchedule(
                cron="0 0 * * *",  # Daily at midnight
                timezone="UTC",
                day_or=True,
                parameters={
                    "questions": [
                        "What are the latest regulatory changes?",
                        "Identify recent legal issues.",
                    ],
                    "datasets": ["latest_financials.csv", "environmental_reports.json"],
                },
            )
        ),
        enforce_parameter_schema=True,  # Ensure parameters match flow signature
    )

    # Apply the deployment
    deployment.apply()
