"""Unit tests for the CompanyAnalysisDeployment class."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from prefect.filesystems import LocalFileSystem
from prefect.infrastructure import Process
from prefect.server.schemas.schedules import CronSchedule
from pytest_mock import MockerFixture

from dewey.core.research.deployment.company_analysis_deployment import (
    CompanyAnalysisDeployment,
    analyze_companies,
)
from dewey.core.base_script import BaseScript


class TestCompanyAnalysisDeployment:
    """Tests for the CompanyAnalysisDeployment class."""

    @pytest.fixture
    def company_analysis_deployment(self, mocker: MockerFixture) -> CompanyAnalysisDeployment:
        """Fixture for creating a CompanyAnalysisDeployment instance."""
        # Mock the BaseScript.__init__ to avoid actual config loading and logging setup
        mocker.patch.object(BaseScript, "__init__", return_value=None)
        deployment = CompanyAnalysisDeployment()
        deployment.name = "TestDeployment"  # Set name for testing purposes
        deployment.description = "Test Description"  # Set description for testing purposes
        return deployment

    @pytest.fixture
    def mock_os_environ(self, mocker: MockerFixture) -> MagicMock:
        """Fixture for mocking environment variables."""
        mock_environ = mocker.patch.dict(os.environ, {
            "PREFECT_AUTH_USER": "test_user",
            "BASIC_AUTH_PASSWORD": "test_password",
        })
        return mock_environ

    @pytest.fixture
    def mock_config_values(self, company_analysis_deployment: CompanyAnalysisDeployment, mocker: MockerFixture) -> None:
        """Fixture for mocking configuration values."""
        mocker.patch.object(
            company_analysis_deployment,
            "get_config_value",
            side_effect=lambda key: {
                "settings.prefect_api_base": "https://test_api_base.com/api",
                "prefect_flows_dir": "/tmp/test_flows_dir",
                "prefect_configs_dir": "/tmp/test_configs_dir",
            }[key],
        )

    @patch("dewey.core.research.deployment.company_analysis_deployment.Deployment.build_from_flow")
    @patch("dewey.core.research.deployment.company_analysis_deployment.LocalFileSystem")
    @patch("dewey.core.research.deployment.company_analysis_deployment.Process")
    def test_deploy(
        self,
        mock_process: MagicMock,
        mock_local_file_system: MagicMock,
        mock_deployment_build: MagicMock,
        company_analysis_deployment: CompanyAnalysisDeployment,
        mock_os_environ: MagicMock,
        mock_config_values: None,
    ) -> None:
        """Test the deploy method."""
        company_analysis_deployment.logger = MagicMock()

        # Call the deploy method
        company_analysis_deployment.deploy()

        # Assert that LocalFileSystem is called with the correct arguments
        mock_local_file_system.assert_called_once_with(
            basepath=str(Path("/tmp/test_flows_dir")),
            persist_local=True,
        )

        # Assert that Process is called with the correct arguments
        mock_process.assert_called_once_with(
            env={"PREFECT_API_URL": "https://test_user:test_password@test_api_base.com/api"}
        )

        # Assert that Deployment.build_from_flow is called with the correct arguments
        mock_deployment_build.assert_called_once()
        call_kwargs = mock_deployment_build.call_args.kwargs
        assert call_kwargs["flow"] == analyze_companies
        assert call_kwargs["name"] == "company-analysis"
        assert call_kwargs["version"] == "1"
        assert call_kwargs["work_queue_name"] == "default"
        assert isinstance(call_kwargs["storage"], LocalFileSystem)
        assert isinstance(call_kwargs["infrastructure"], Process)
        assert call_kwargs["path"] == "company_analysis.py"
        assert call_kwargs["description"] == "Analyzes companies for controversies using LLM models"
        assert call_kwargs["parameters"] == {"config_path": str(Path("/tmp/test_configs_dir") / "latest_config.json")}
        assert call_kwargs["tags"] == ["company-analysis", "llm", "production"]
        assert isinstance(call_kwargs["schedule"], CronSchedule)
        assert call_kwargs["schedule"].cron == "0 0 * * *"
        assert call_kwargs["schedule"].timezone == "UTC"

        # Assert that deployment.apply() is called
        deployment_instance = mock_deployment_build.return_value
        deployment_instance.apply.assert_called_once()

        # Assert that the logger info method is called
        company_analysis_deployment.logger.info.assert_called_once_with(
            "Company analysis deployment created successfully"
        )

    @patch("dewey.core.research.deployment.company_analysis_deployment.CompanyAnalysisDeployment.deploy")
    def test_run(
        self,
        mock_deploy: MagicMock,
        company_analysis_deployment: CompanyAnalysisDeployment,
    ) -> None:
        """Test the run method."""
        # Call the run method
        company_analysis_deployment.run()

        # Assert that the deploy method is called
        mock_deploy.assert_called_once()

    @patch(
        "dewey.core.research.deployment.company_analysis_deployment.CompanyAnalysisDeployment.execute"
    )
    def test_main(self, mock_execute: MagicMock) -> None:
        """Test the main function."""
        # Patch the CompanyAnalysisDeployment class to avoid actual initialization
        with patch(
            "dewey.core.research.deployment.company_analysis_deployment.CompanyAnalysisDeployment"
        ) as MockCompanyAnalysisDeployment:
            # Call the main function
from dewey.core.research.deployment.company_analysis_deployment import main

            main()

            # Assert that CompanyAnalysisDeployment is instantiated
            MockCompanyAnalysisDeployment.assert_called_once()

            # Assert that the execute method is called on the instance
            instance = MockCompanyAnalysisDeployment.return_value
            mock_execute.assert_called_once()

    def test_initialization(self, mocker: MockerFixture) -> None:
        """Test the __init__ method."""
        # Mock the necessary methods to avoid external dependencies
        mocker.patch.object(BaseScript, "__init__", return_value=None)
        mocker.patch.object(CompanyAnalysisDeployment, "_setup_logging", return_value=None)
        mocker.patch.object(CompanyAnalysisDeployment, "_load_config", return_value={})
        mocker.patch.object(CompanyAnalysisDeployment, "_initialize_db_connection", return_value=None)
        mocker.patch.object(CompanyAnalysisDeployment, "_initialize_llm_client", return_value=None)

        # Create an instance of CompanyAnalysisDeployment
        deployment = CompanyAnalysisDeployment()

        # Assert that the attributes are initialized correctly
        assert deployment.name == "CompanyAnalysisDeployment"
        assert deployment.description == "Deploys company analysis flow to Prefect."
        assert deployment.config_section == "paths"
        # Verify that the mocked methods were called
        deployment._setup_logging.assert_called_once()
        deployment._load_config.assert_called_once()

