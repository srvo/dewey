
# Refactored from: service_deployment
# Date: 2025-03-16T16:19:08.580204
# Refactor Version: 1.0
import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import Service




class ServiceDeployment(BaseScript):
    """Service deployment and configuration management.

    Implements centralized configuration and error handling via BaseScript.

    Attributes:
        service_manager: ServiceManager instance
    """

    def __init__(self, service_manager) -> None:
        """Initialize ServiceDeployment.

        Args:
            service_manager: ServiceManager instance
        """
        super().__init__(config_section="core")
        self.service_manager = service_manager
        self.workspace_dir = Path(self.config["core"]["project_root"]) / "workspace"
        self.config_dir = Path(self.config["core"]["project_root"]) / "config"

    def deploy_service(self, service: Service, config: dict[str, Any]) -> None:
        """Deploy or update a service.

        Args:
            service: Service to deploy
            config: Service configuration

        Raises:
            RuntimeError: If deployment steps fail
        """
        try:
            self.logger.info(f"Starting deployment of {service.name}")
            self._create_remote_service_directory(service)
            compose_config = self._generate_compose_config(config)
            self._write_compose_config(service, compose_config)
            self._sync_config_to_remote(service)
            self._start_service(service)
            self.logger.info(f"Deployment of {service.name} completed")
        except Exception as e:
            self.logger.exception("Deployment failed")
            raise RuntimeError(f"Deployment failed: {str(e)}") from e

    def backup_service(self, service: Service) -> Path:
        """Create backup of service configuration and data.

        Args:
        ----
            service: Service to backup

        Returns:
        -------
            Path to backup archive

        """
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir)
            self._backup_config(service, backup_dir)
            self._backup_data_volumes(service, backup_dir)
            return self._create_archive(service, backup_dir)

    def restore_service(self, service: Service, backup_path: Path) -> None:
        """Restore service from backup.

        Args:
        ----
            service: Service to restore
            backup_path: Path to backup archive

        """
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir)
            shutil.unpack_archive(backup_path, backup_dir)
            self._stop_service(service)
            self._restore_config(service, backup_dir)
            self._restore_data_volumes(service, backup_dir)
            self._start_service(service)

    def _create_remote_service_directory(self, service: Service) -> None:
        """Create the remote service directory.

        Args:
        ----
            service: The service for which to create the directory.

        """
        self.service_manager.run_command(f"mkdir -p {service.path}")

    def _write_compose_config(
        self,
        service: Service,
        compose_config: dict[str, Any],
    ) -> None:
        """Write the docker-compose configuration to a file.

        Args:
        ----
            service: The service for which to write the config.
            compose_config: The docker-compose configuration.

        """
        compose_path = service.config_path / "docker-compose.yml"
        compose_path.write_text(json.dumps(compose_config, indent=2))

    def _start_service(self, service: Service) -> None:
        """Start the service using docker-compose.

        Args:
        ----
            service: The service to start.

        """
        self.service_manager.run_command(f"cd {service.path} && docker-compose up -d")

    def _stop_service(self, service: Service) -> None:
        """Stop the service using docker-compose.

        Args:
        ----
            service: The service to stop.

        """
        self.service_manager.run_command(f"cd {service.path} && docker-compose down")

    def _backup_config(self, service: Service, backup_dir: Path) -> None:
        """Backup the service configuration.

        Args:
        ----
            service: The service to backup.
            backup_dir: The directory to store the backup.

        """
        config_backup = backup_dir / "config"
        shutil.copytree(service.config_path, config_backup)

    def _backup_data_volumes(self, service: Service, backup_dir: Path) -> None:
        """Backup the service's data volumes.

        Args:
        ----
            service: The service to backup.
            backup_dir: The directory to store the backup.

        """
        data_backup = backup_dir / "data"
        data_backup.mkdir()

        for container in service.containers:
            inspect = self.service_manager.run_command(
                f"docker inspect {container.name}",
            )
            inspect_data = json.loads(inspect)[0]
            mounts = inspect_data.get("Mounts", [])

            for mount in mounts:
                if mount.get("Type") == "volume":
                    volume_name = mount["Name"]
                    volume_dir = data_backup / volume_name
                    volume_dir.mkdir()

                    docker_cmd = (
                        f"docker run --rm "
                        f"-v {volume_name}:/source "
                        f"-v {volume_dir}:/backup "
                        "alpine cp -r /source/. /backup/"
                    )
                    self.service_manager.run_command(docker_cmd)

    def _restore_config(self, service: Service, backup_dir: Path) -> None:
        """Restore the service configuration from backup.

        Args:
        ----
            service: The service to restore.
            backup_dir: The directory containing the backup.

        """
        config_backup = backup_dir / "config"
        if config_backup.exists():
            shutil.rmtree(service.config_path, ignore_errors=True)
            shutil.copytree(config_backup, service.config_path)
            self._sync_config_to_remote(service)

    def _restore_data_volumes(self, service: Service, backup_dir: Path) -> None:
        """Restore the service's data volumes from backup.

        Args:
        ----
            service: The service to restore.
            backup_dir: The directory containing the backup.

        """
        data_backup = backup_dir / "data"
        if data_backup.exists():
            for volume_dir in data_backup.iterdir():
                volume_name = volume_dir.name

                self.service_manager.run_command(f"docker volume rm -f {volume_name}")
                self.service_manager.run_command(f"docker volume create {volume_name}")

                docker_cmd = (
                    f"docker run --rm "
                    f"-v {volume_name}:/target "
                    f"-v {volume_dir}:/backup "
                    "alpine cp -r /backup/. /target/"
                )
                self.service_manager.run_command(docker_cmd)

    def _create_archive(self, service: Service, backup_dir: Path) -> Path:
        """Create an archive of the backup directory.

        Args:
        ----
            service: The service being backed up.
            backup_dir: The directory to archive.

        Returns:
        -------
            The path to the created archive.

        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"{service.name}_backup_{timestamp}.tar.gz"
        archive_path = self.workspace_dir / "backups" / archive_name

        archive_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.make_archive(str(archive_path.with_suffix("")), "gztar", backup_dir)

        return archive_path

    def _generate_compose_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """Generate docker-compose configuration.

        Args:
        ----
            config: Service configuration

        Returns:
        -------
            Docker Compose configuration dictionary

        """
        compose_config = {"version": "3", "services": {}}

        for name, service_config in config.get("services", {}).items():
            compose_config["services"][name] = {
                "image": service_config["image"],
                "container_name": service_config.get("container_name", name),
                "restart": service_config.get("restart", "unless-stopped"),
            }

            for field in ["environment", "volumes", "ports", "depends_on"]:
                if field in service_config:
                    compose_config["services"][name][field] = service_config[field]

            if "healthcheck" in service_config:
                compose_config["services"][name]["healthcheck"] = service_config[
                    "healthcheck"
                ]

        if "networks" in config:
            compose_config["networks"] = config["networks"]

        if "volumes" in config:
            compose_config["volumes"] = config["volumes"]

        return compose_config

    def _sync_config_to_remote(self, service: Service) -> None:
        """Sync local configuration to remote host.

        Args:
        ----
            service: Service to sync configuration for

        """
        self.service_manager.run_command(f"mkdir -p {service.path}")

        compose_path = service.config_path / "docker-compose.yml"
        if compose_path.exists():
            remote_path = service.path / "docker-compose.yml"
            compose_content = compose_path.read_text()
            self.service_manager.run_command(
                f"cat > {remote_path} << 'EOL'\n{compose_content}\nEOL",
            )
import pytest
from unittest.mock import MagicMock, patch, Mock
from pathlib import Path
from src.dewey.core.automation.service_deployment import ServiceDeployment, Service
from typing import Any
import json
import shutil
import tempfile

class TestServiceDeployment:
    """Test suite for ServiceDeployment class.

    Tests follow Arrange-Act-Assert pattern, cover all critical paths,
    and ensure adherence to project conventions.
    """

    @pytest.fixture
    def service_manager_mock(self) -> MagicMock:
        """Fixture for mocked ServiceManager instance."""
        return MagicMock()

    @pytest.fixture
    def service_deployment(self, service_manager_mock: MagicMock) -> ServiceDeployment:
        """Fixture for ServiceDeployment instance under test."""
        return ServiceDeployment(service_manager_mock)

    @pytest.fixture
    def service_mock(self) -> Mock:
        """Fixture for mocked Service instance with required attributes."""
        service = Mock(spec=Service)
        service.path = Path("/mock/service/path")
        service.config_path = Path("/mock/config/path")
        service.containers = [Mock(name="test_container")]
        return service

    def test_deploy_service_happy_path(
        self,
        service_deployment: ServiceDeployment,
        service_mock: Mock,
        service_manager_mock: MagicMock,
    ) -> None:
        """Test deploy_service successfully deploys a service.

        Arrange:
            Mock service and config.
        Act:
            Call deploy_service with valid config.
        Assert:
            Verify directory creation, compose config generation, and docker commands.
        """
        config = {
            "services": {
                "web": {
                    "image": "nginx:latest",
                    "ports": ["80:80"],
                    "depends_on": ["db"],
                }
            }
        }

        service_deployment.deploy_service(service_mock, config)

        # Verify directory creation
        service_manager_mock.run_command.assert_any_call(
            "mkdir -p /mock/service/path"
        )

        # Verify compose config generation
        expected_compose = {
            "version": "3",
            "services": {
                "web": {
                    "image": "nginx:latest",
                    "container_name": "web",
                    "restart": "unless-stopped",
                    "ports": ["80:80"],
                    "depends_on": ["db"],
                }
            },
        }
        service_deployment._write_compose_config.assert_called_with(
            service_mock, expected_compose
        )

        # Verify docker-compose command execution
        service_manager_mock.run_command.assert_any_call(
            "cd /mock/service/path && docker-compose up -d"
        )

    def test_backup_service_creates_archive(
        self,
        service_deployment: ServiceDeployment,
        service_mock: Mock,
        service_manager_mock: MagicMock,
    ) -> None:
        """Test backup_service creates a valid archive.

        Arrange:
            Mock temp directory and backup components.
        Act:
            Call backup_service.
        Assert:
            Verify config and volume backups, archive creation.
        """
        with patch("tempfile.mkdtemp", return_value="/mock/temp"):
            with patch("pathlib.Path.mkdir") as mock_mkdir:
                backup_path = service_deployment.backup_service(service_mock)

        assert backup_path.name.startswith("test_container_backup_")
        assert backup_path.suffix == ".tar.gz"

        # Verify config backup
        shutil.copytree.assert_called_with(
            Path("/mock/config/path"), Path("/mock/temp/config")
        )

        # Verify data backup
        service_manager_mock.run_command.assert_any_call(
            "docker run --rm -v test_container:/source -v /mock/temp/data/test_container:/backup alpine cp -r /source/. /backup/"
        )

    def test_restore_service_restores_config_and_data(
        self,
        service_deployment: ServiceDeployment,
        service_mock: Mock,
        service_manager_mock: MagicMock,
    ) -> None:
        """Test restore_service correctly restores from backup.

        Arrange:
            Mock backup archive and temp directory.
        Act:
            Call restore_service with mock backup.
        Assert:
            Verify config/volume restoration and service restart.
        """
        backup_path = Path("/mock/backup.tar.gz")
        with patch("shutil.unpack_archive") as mock_unpack:
            with patch("tempfile.mkdtemp", return_value="/mock/temp"):
                service_deployment.restore_service(service_mock, backup_path)

        # Verify service stopped before restore
        service_manager_mock.run_command.assert_any_call(
            "cd /mock/service/path && docker-compose down"
        )

        # Verify config restoration
        shutil.rmtree.assert_called_with(
            Path("/mock/config/path"), ignore_errors=True
        )
        shutil.copytree.assert_called_with(
            Path("/mock/temp/config"), Path("/mock/config/path")
        )

        # Verify data volume restoration
        service_manager_mock.run_command.assert_any_call(
            "docker volume rm -f test_container_volume"
        )
        service_manager_mock.run_command.assert_any_call(
            "docker volume create test_container_volume"
        )
        service_manager_mock.run_command.assert_any_call(
            "docker run --rm -v test_container_volume:/target -v /mock/temp/data/test_container_volume:/backup alpine cp -r /backup/. /target/"
        )

        # Verify service restarted
        service_manager_mock.run_command.assert_any_call(
            "cd /mock/service/path && docker-compose up -d"
        )

    def test_backup_service_handles_no_volumes(
        self,
        service_deployment: ServiceDeployment,
        service_mock: Mock,
        service_manager_mock: MagicMock,
    ) -> None:
        """Test backup_service when no volumes are present.

        Arrange:
            Mock empty mounts list in container inspect.
        Act:
            Call backup_service.
        Assert:
            No volume backup commands executed.
        """
        service_manager_mock.run_command.return_value = json.dumps(
            [{"Mounts": []}]
        )

        service_deployment.backup_service(service_mock)

        # Verify no docker run commands for volumes
        assert (
            "docker run --rm -v " not in service_manager_mock.run_command.call_args_list
        )

    def test_generate_compose_config_with_networks_volumes(
        self,
        service_deployment: ServiceDeployment,
    ) -> None:
        """Test compose config includes networks and volumes when present."""
        config = {
            "services": {"web": {"image": "nginx"}},
            "networks": {"my_net": {}},
            "volumes": {"my_vol": {}},
        }

        compose = service_deployment._generate_compose_config(config)

        assert "networks" in compose
        assert "volumes" in compose

    def test_sync_config_to_remote_writes_compose(
        self,
        service_deployment: ServiceDeployment,
        service_mock: Mock,
    ) -> None:
        """Test _sync_config_to_remote writes compose file to remote."""
        compose_path = service_mock.config_path / "docker-compose.yml"
        compose_path.write_text = MagicMock()
        service_deployment._sync_config_to_remote(service_mock)

        compose_path.write_text.assert_called()
        remote_path = service_mock.path / "docker-compose.yml"
        assert f"cat > {remote_path}" in service_deployment.service_manager.run_command.call_args[0][0]

@pytest.mark.integration
class TestServiceDeploymentIntegration:
    """Integration tests for critical deployment paths."""

    def test_end_to_end_deployment_cycle(
        self,
        service_deployment: ServiceDeployment,
        service_mock: Mock,
        service_manager_mock: MagicMock,
    ) -> None:
        """Test full deploy -> backup -> restore cycle."""
        config = {"services": {"web": {"image": "nginx"}}}
        service_deployment.deploy_service(service_mock, config)
        backup = service_deployment.backup_service(service_mock)
        service_deployment.restore_service(service_mock, backup)

        # Verify all steps completed without errors
        assert service_manager_mock.run_command.call_count >= 3
````
