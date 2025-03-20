import logging
from unittest.mock import MagicMock, patch
import pytest
from dewey.core.research.deployment import DeploymentModule
from dewey.core.base_script import BaseScript


class TestDeploymentModule:
    """Tests for the DeploymentModule class."""

    @pytest.fixture
    def deployment_module(self) -> DeploymentModule:
        """Fixture for creating a DeploymentModule instance."""
        return DeploymentModule()

    def test_inheritance(self, deployment_module: DeploymentModule) -> None:
        """Test that DeploymentModule inherits from BaseScript."""
        assert isinstance(deployment_module, BaseScript)

    def test_init_default(self) -> None:
        """Test the __init__ method with default arguments."""
        module = DeploymentModule()
        assert module.config_section == "deployment"
        assert module.requires_db is False
        assert module.enable_llm is False
        assert module.name == "DeploymentModule"
        assert module.description == "Base class for deployment modules."

    def test_init_custom(self) -> None:
        """Test the __init__ method with custom arguments."""
        module = DeploymentModule(
            config_section="custom", requires_db=True, enable_llm=True, arg1="value1"
        )
        assert module.config_section == "custom"
        assert module.requires_db is True
        assert module.enable_llm is True

    def test_run_no_db_no_llm(self, deployment_module: DeploymentModule, caplog: pytest.LogCaptureFixture) -> None:
        """Test the run method without database or LLM."""
        caplog.set_level(logging.INFO)
        deployment_module.run()
        assert "Deployment module started." in caplog.text
        assert "Example config value: default_value" in caplog.text
        assert "Deployment module finished." in caplog.text
        assert "Database connection test" not in caplog.text
        assert "LLM response" not in caplog.text

    @patch("dewey.core.research.deployment.DeploymentModule.get_config_value")
    def test_run_config_value(
        self, mock_get_config_value: MagicMock, deployment_module: DeploymentModule, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that the run method retrieves and logs a config value."""
        mock_get_config_value.return_value = "test_config_value"
        caplog.set_level(logging.INFO)
        deployment_module.run()
        mock_get_config_value.assert_called_with("example_config_key", "default_value")
        assert "Example config value: test_config_value" in caplog.text

    def test_run_with_db(self, deployment_module: DeploymentModule, caplog: pytest.LogCaptureFixture) -> None:
        """Test the run method with database."""
        deployment_module.requires_db = True
        deployment_module.db_conn = MagicMock()
        cursor_mock = MagicMock()
        deployment_module.db_conn.cursor.return_value = cursor_mock
        cursor_mock.fetchone.return_value = [1]
        caplog.set_level(logging.INFO)
        deployment_module.run()
        assert "Database connection test: [1]" in caplog.text

    def test_run_with_llm(self, deployment_module: DeploymentModule, caplog: pytest.LogCaptureFixture) -> None:
        """Test the run method with LLM."""
        deployment_module.enable_llm = True
        deployment_module.llm_client = MagicMock()
        deployment_module.llm_client.generate.return_value = "Test LLM response"
        caplog.set_level(logging.INFO)
        deployment_module.run()
        assert "LLM response: Test LLM response" in caplog.text

    def test_run_db_error(self, deployment_module: DeploymentModule, caplog: pytest.LogCaptureFixture) -> None:
        """Test the run method with a database error."""
        deployment_module.requires_db = True
        deployment_module.db_conn = MagicMock()
        deployment_module.db_conn.cursor.side_effect = Exception("DB Error")
        caplog.set_level(logging.ERROR)
        deployment_module.run()
        assert "Database error: DB Error" in caplog.text

    def test_run_llm_error(self, deployment_module: DeploymentModule, caplog: pytest.LogCaptureFixture) -> None:
        """Test the run method with an LLM error."""
        deployment_module.enable_llm = True
        deployment_module.llm_client = MagicMock()
        deployment_module.llm_client.generate.side_effect = Exception("LLM Error")
        caplog.set_level(logging.ERROR)
        deployment_module.run()
        assert "LLM error: LLM Error" in caplog.text

    def test_run_deployment_error(self, deployment_module: DeploymentModule, caplog: pytest.LogCaptureFixture) -> None:
        """Test the run method with a deployment error."""
        with patch.object(DeploymentModule, "get_config_value", side_effect=Exception("Deployment Error")):
            caplog.set_level(logging.ERROR)
            with pytest.raises(Exception, match="Deployment failed: Deployment Error"):
                deployment_module.run()
            assert "Deployment failed: Deployment Error" in caplog.text
