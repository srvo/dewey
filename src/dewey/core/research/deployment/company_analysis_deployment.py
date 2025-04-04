"""Company Analysis Deployment Script."""

import os
from pathlib import Path
from typing import Any

from prefect.deployments import Deployment
from prefect.filesystems import LocalFileSystem
from prefect.infrastructure import Process
from prefect.server.schemas.schedules import CronSchedule

from dewey.core.base_script import BaseScript
from dewey.core.research.analysis.company_analysis import analyze_companies


class CompanyAnalysisDeployment(BaseScript):
    """
    Handles deployment of company analysis flow.

    Inherits from BaseScript for standardized configuration and logging.
    """

    def __init__(self) -> None:
        """Initializes the CompanyAnalysisDeployment."""
        super().__init__(
            name="CompanyAnalysisDeployment",
            description="Deploys company analysis flow to Prefect.",
            config_section="paths",  # Assuming relevant paths are under 'paths'
        )

    def execute(self) -> None:
        """Main execution method to deploy the company analysis flow."""
        self.deploy()

    def deploy(self) -> None:
        """Deploys the company analysis flow to Prefect."""
        # Get auth credentials from environment
        prefect_user = os.getenv("PREFECT_AUTH_USER", "srvo")
        prefect_pass = os.getenv("BASIC_AUTH_PASSWORD", "")

        # Get API URL from config
        api_base = self.get_config_value("settings.prefect_api_base")
        api_url = api_base
        if prefect_user and prefect_pass:
            api_url = f"https://{prefect_user}:{prefect_pass}@{api_base.replace('https://', '')}"

        # Get paths from config
        flows_path = Path(self.get_config_value("prefect_flows_dir"))
        config_path = (
            Path(self.get_config_value("prefect_configs_dir")) / "latest_config.json"
        )

        # Create a local storage block for our flow code
        storage = LocalFileSystem(basepath=str(flows_path), persist_local=True)

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
            parameters={"config_path": str(config_path)},
            tags=["company-analysis", "llm", "production"],
            schedule=(
                CronSchedule(
                    cron="0 0 * * *",  # Daily at midnight
                    timezone="UTC",
                )
            ),
        )

        # Apply the deployment
        deployment.apply()
        self.logger.info("Company analysis deployment created successfully")

    def run(self, args: Any | None = None) -> None:
        """
        Main execution method to deploy the company analysis flow.

        Args:
        ----
            args: Optional arguments (not used in this implementation).

        """
        self.deploy()


def main() -> None:
    """Main entry point."""
    deployment = CompanyAnalysisDeployment()
    deployment.execute()


if __name__ == "__main__":
    main()
