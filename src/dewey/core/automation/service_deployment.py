
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


class ServiceDeployment:
    """Manages service deployment, updates, backups, and restores using Docker Compose."""


class ServiceDeployment:
    """Service deployment and configuration management."""

    def __init__(self, service_manager) -> None:
        """Initialize ServiceDeployment.

        Args:
        ----
            service_manager: ServiceManager instance

        """
        self.service_manager = service_manager
        self.workspace_dir = service_manager.workspace
        self.config_dir = service_manager.config_dir

    def deploy_service(self, service: Service, config: dict[str, Any]) -> None:
        """Deploy or update a service.

        Args:
        ----
            service: Service to deploy
            config: Service configuration

        """
        self._create_remote_service_directory(service)
        compose_config = self._generate_compose_config(config)
        self._write_compose_config(service, compose_config)
        self._sync_config_to_remote(service)
        self._start_service(service)

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
