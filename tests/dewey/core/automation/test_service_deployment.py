import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.dewey.core.automation.models import Service
from src.dewey.core.automation.service_deployment import ServiceDeployment


class TestServiceDeployment:
    """Tests for the ServiceDeployment class."""

    @pytest.fixture
    def mock_service_manager(self) -> MagicMock:
        """Fixture to create a mock ServiceManager."""
        return MagicMock()

    @pytest.fixture
    def service_deployment(self, mock_service_manager: MagicMock) -> ServiceDeployment:
        """Fixture to create a ServiceDeployment instance with a mock ServiceManager."""
        return ServiceDeployment(mock_service_manager)

    @pytest.fixture
    def mock_service(self, tmp_path: Path) -> Service:
        """Fixture to create a mock Service instance."""
        service = Service(
            name="test_service",
            path=tmp_path / "service_path",
            config_path=tmp_path / "config_path",
            containers=[],
        )
        service.config_path.mkdir(parents=True, exist_ok=True)
        return service

    def test__sync_config_to_remote_normal_case(
        self,
        service_deployment: ServiceDeployment,
        mock_service: Service,
        mock_service_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test syncing configuration to remote host in the normal case."""
        compose_path = mock_service.config_path / "docker-compose.yml"
        compose_content = "version: '3'\nservices:\n  web:\n    image: nginx:latest"
        compose_path.write_text(compose_content)

        service_deployment._sync_config_to_remote(mock_service)

        mock_service_manager.run_command.assert_called_with(
            f"mkdir -p {mock_service.path}",
        )
        mock_service_manager.run_command.assert_called_with(
            f"cat > {mock_service.path / 'docker-compose.yml'} << 'EOL'\n{compose_content}\nEOL",
        )

    def test__sync_config_to_remote_config_file_does_not_exist(
        self,
        service_deployment: ServiceDeployment,
        mock_service: Service,
        mock_service_manager: MagicMock,
    ) -> None:
        """Test syncing configuration when the config file does not exist."""
        service_deployment._sync_config_to_remote(mock_service)

        mock_service_manager.run_command.assert_called_once_with(
            f"mkdir -p {mock_service.path}",
        )

    def test__sync_config_to_remote_empty_config_file(
        self,
        service_deployment: ServiceDeployment,
        mock_service: Service,
        mock_service_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test syncing configuration with an empty config file."""
        compose_path = mock_service.config_path / "docker-compose.yml"
        compose_path.write_text("")

        service_deployment._sync_config_to_remote(mock_service)

        mock_service_manager.run_command.assert_called_with(
            f"mkdir -p {mock_service.path}",
        )
        mock_service_manager.run_command.assert_called_with(
            f"cat > {mock_service.path / 'docker-compose.yml'} << 'EOL'\n\nEOL",
        )

    def test__sync_config_to_remote_long_config_file(
        self,
        service_deployment: ServiceDeployment,
        mock_service: Service,
        mock_service_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test syncing configuration with a long config file."""
        compose_path = mock_service.config_path / "docker-compose.yml"
        compose_content = "version: '3'\n" + "services:\n" * 50 + "  web:\n    image: nginx:latest"
        compose_path.write_text(compose_content)

        service_deployment._sync_config_to_remote(mock_service)

        mock_service_manager.run_command.assert_called_with(
            f"mkdir -p {mock_service.path}",
        )
        mock_service_manager.run_command.assert_called_with(
            f"cat > {mock_service.path / 'docker-compose.yml'} << 'EOL'\n{compose_content}\nEOL",
        )

    def test__sync_config_to_remote_special_characters_in_config(
        self,
        service_deployment: ServiceDeployment,
        mock_service: Service,
        mock_service_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test syncing configuration with special characters in the config file."""
        compose_path = mock_service.config_path / "docker-compose.yml"
        compose_content = "version: '3'\nservices:\n  web:\n    image: nginx:latest\n    environment:\n      - KEY=value with spaces and !@#$%^&*()"
        compose_path.write_text(compose_content)

        service_deployment._sync_config_to_remote(mock_service)

        mock_service_manager.run_command.assert_called_with(
            f"mkdir -p {mock_service.path}",
        )
        mock_service_manager.run_command.assert_called_with(
            f"cat > {mock_service.path / 'docker-compose.yml'} << 'EOL'\n{compose_content}\nEOL",
        )
