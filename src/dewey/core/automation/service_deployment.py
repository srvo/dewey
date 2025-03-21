# Refactored from: service_deployment
# Date: 2025-03-16T16:19:08.580204
# Refactor Version: 1.0
import json
import shutil
import tempfile
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Protocol

from dewey.core.base_script import BaseScript
from dewey.core.db.connection import DatabaseConnection
from dewey.core.db.connection import get_connection as get_local_connection
from dewey.core.db.connection import (
    get_motherduck_connection as get_motherduck_connection,
)

from .models import Service


class ServiceManagerInterface(Protocol):
    """Interface for Service Managers."""

    def run_command(self, command: str) -> None:
        ...


class FileSystemInterface(Protocol):
    """Interface for file system operations."""

    def exists(self, path: Path) -> bool:
        ...

    def mkdir(self, path: Path, parents: bool = False, exist_ok: bool = False) -> None:
        ...

    def copytree(self, src: Path, dst: Path, dirs_exist_ok: bool = False) -> None:
        ...

    def copy2(self, src: Path, dst: Path) -> None:
        ...

    def unpack_archive(self, filename: str, extract_dir: str) -> None:
        ...

    def make_archive(self, base_name: str, format: str, root_dir: str) -> str:
        ...

    def rmtree(self, path: Path) -> None:
        ...

    def write_text(self, path: Path, data: str) -> None:
        ...

    def read_text(self, path: Path) -> str:
        ...

    def iterdir(self, path: Path):
        ...

    def is_file(self, path: Path) -> bool:
        ...

    def is_dir(self, path: Path) -> bool:
        ...


class RealFileSystem:
    """Real file system operations."""

    def exists(self, path: Path) -> bool:
        return path.exists()

    def mkdir(self, path: Path, parents: bool = False, exist_ok: bool = False) -> None:
        path.mkdir(parents=parents, exist_ok=exist_ok)

    def copytree(self, src: Path, dst: Path, dirs_exist_ok: bool = False) -> None:
        shutil.copytree(src, dst, dirs_exist_ok=dirs_exist_ok)

    def copy2(self, src: Path, dst: Path) -> None:
        shutil.copy2(src, dst)

    def unpack_archive(self, filename: str, extract_dir: str) -> None:
        shutil.unpack_archive(filename, extract_dir)

    def make_archive(self, base_name: str, format: str, root_dir: str) -> str:
        return shutil.make_archive(base_name, format, root_dir)

    def rmtree(self, path: Path) -> None:
        shutil.rmtree(path)

    def write_text(self, path: Path, data: str) -> None:
        path.write_text(data)

    def read_text(self, path: Path) -> str:
        return path.read_text()

    def iterdir(self, path: Path):
        return path.iterdir()

    def is_file(self, path: Path) -> bool:
        return path.is_file()

    def is_dir(self, path: Path) -> bool:
        return path.is_dir()


class ServiceDeployment(BaseScript):
    """Service deployment and configuration management.

    Implements centralized configuration and error handling via BaseScript.
    """

    def __init__(
        self,
        service_manager: ServiceManagerInterface,
        fs: FileSystemInterface,
        json_lib=json,
        shutil_lib=shutil,
    ) -> None:
        """Initialize ServiceDeployment."""
        super().__init__(
            name="service_deployment",
            description="Service deployment and configuration management",
            config_section="service_deployment",
            requires_db=False,
            enable_llm=False,
        )
        self.service_manager = service_manager
        self.workspace_dir = (
            Path(self.get_config_value("paths.project_root")) / "workspace"
        )
        self.config_dir = (
            Path(self.get_config_value("paths.project_root")) / "config"
        )
        self.backups_dir = self.workspace_dir / "backups"
        fs.mkdir(self.backups_dir, parents=True, exist_ok=True)
        self.fs = fs
        self.json = json_lib
        self.shutil = shutil_lib

    def run(self, service_manager: ServiceManagerInterface) -> None:
        """Runs the service deployment process.

        Args:
            service_manager: ServiceManager instance.
        """
        # self.service_manager = service_manager # No longer needed

        pass

    def _ensure_service_dirs(self, service: Service) -> None:
        """Ensure service directories exist.

        Args:
            service: Service to create directories for.

        Raises:
            RuntimeError: If directories cannot be created.
        """
        try:
            # Create parent directories first
            self.fs.mkdir(service.path.parent, parents=True, exist_ok=True)
            self.fs.mkdir(service.config_path.parent, parents=True, exist_ok=True)

            # Then create the actual service directories
            self.fs.mkdir(service.path, exist_ok=True)
            self.fs.mkdir(service.config_path, exist_ok=True)
        except OSError as e:
            self.logger.error(f"Failed to create service directories: {e}")
            raise RuntimeError(f"Failed to create service directories: {e}")

    def deploy_service(self, service: Service, config: Dict[str, Any]) -> None:
        """Deploy or update a service.

        Args:
            service: Service to deploy.
            config: Service configuration.

        Raises:
            RuntimeError: If deployment steps fail.
        """
        try:
            self._ensure_service_dirs(service)
            compose_config = self._generate_compose_config(config)
            self._write_compose_config(service, compose_config)
            self._start_service(service)
        except Exception as e:
            self.logger.exception("Deployment failed")
            raise RuntimeError(f"Deployment failed: {str(e)}") from e

    def _generate_compose_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate docker-compose configuration.

        Args:
            config: Service configuration.

        Returns:
            Docker Compose configuration dictionary.

        Raises:
            KeyError: If a service is missing the 'image' field.
        """
        compose_config = {"version": "3", "services": {}}

        for name, service_config in config.get("services", {}).items():
            if "image" not in service_config:
                self.logger.error(f"Missing required 'image' field for service {name}")
                raise KeyError(f"Missing required 'image' field for service {name}")

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

    def _write_compose_config(self, service: Service, config: Dict[str, Any]) -> None:
        """Write docker-compose configuration to file.

        Args:
            service: Service to write config for.
            config: Docker Compose configuration.
        """
        compose_file = service.config_path / "docker-compose.yml"
        self.fs.write_text(compose_file, self.json.dumps(config, indent=2))

    def _generate_timestamp(self) -> str:
        """Generate a timestamp string."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _create_archive(self, service: Service, backup_dir: Path) -> Path:
        """Create a backup archive from a backup directory.

        Args:
            service: Service being backed up.
            backup_dir: Directory containing files to archive.

        Returns:
            Path to created archive.

        Raises:
            RuntimeError: If archive creation fails.
        """
        try:
            # Ensure backups directory exists
            self.fs.mkdir(self.backups_dir, parents=True, exist_ok=True)

            # Generate archive name with timestamp
            timestamp = self._generate_timestamp()
            archive_name = f"{service.name}_backup_{timestamp}.tar.gz"
            archive_path = self.backups_dir / archive_name

            # Create archive
            self.fs.make_archive(
                str(archive_path.with_suffix("")),
                "gztar",
                str(backup_dir),
            )

            return archive_path
        except Exception as e:
            self.logger.exception(f"Failed to create archive: {str(e)}")
            raise RuntimeError(f"Failed to create archive: {str(e)}") from e

    def backup_service(self, service: Service) -> Path:
        """Back up service configuration and data.

        Args:
            service: Service to back up.

        Returns:
            Path to backup archive.

        Raises:
            RuntimeError: If backup fails.
        """
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                backup_dir = Path(temp_dir)
                self._backup_config(service, backup_dir)
                self._backup_data_volumes(service, backup_dir)
                return self._create_archive(service, backup_dir)
        except Exception as e:
            self.logger.exception("Service backup failed")
            raise RuntimeError(f"Service backup failed: {str(e)}") from e

    def restore_service(self, service: Service, backup_path: Path) -> None:
        """Restore service from backup.

        Args:
            service: Service to restore.
            backup_path: Path to backup archive.

        Raises:
            RuntimeError: If restore fails.
            FileNotFoundError: If backup file doesn't exist.
        """
        if not self.fs.exists(backup_path):
            self.logger.error(f"Backup file not found: {backup_path}")
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                backup_dir = Path(temp_dir)
                self._ensure_service_dirs(service)

                # Stop service and restore from backup
                self._stop_service(service)
                self.fs.unpack_archive(str(backup_path), str(backup_dir))
                self._restore_config(service, backup_dir)
                self._restore_data_volumes(service, backup_dir)
                self._start_service(service)
        except Exception as e:
            self.logger.exception("Service restore failed")
            raise RuntimeError(f"Service restore failed: {str(e)}") from e

    def _start_service(self, service: Service) -> None:
        """Start the service using docker-compose.

        Args:
            service: The service to start.
        """
        self.service_manager.run_command(f"cd {service.path} && docker-compose up -d")

    def _stop_service(self, service: Service) -> None:
        """Stop the service using docker-compose.

        Args:
            service: The service to stop.
        """
        self.service_manager.run_command(f"cd {service.path} && docker-compose down")

    def _backup_config(self, service: Service, backup_dir: Path) -> None:
        """Backup service configuration.

        Args:
            service: Service to backup.
            backup_dir: Directory to store backup.

        Raises:
            RuntimeError: If backup fails.
        """
        try:
            # Create config backup directory
            config_backup = backup_dir / "config"
            self.fs.mkdir(config_backup, parents=True, exist_ok=True)

            # Copy config if it exists
            if self.fs.exists(service.config_path):
                self.fs.copytree(service.config_path, config_backup, dirs_exist_ok=True)
        except Exception as e:
            self.logger.exception(f"Failed to backup config: {str(e)}")
            raise RuntimeError(f"Failed to backup config: {str(e)}") from e

    def _backup_data_volumes(self, service: Service, backup_dir: Path) -> None:
        """Backup the service's data volumes.

        Args:
            service: The service to backup.
            backup_dir: The directory to store the backup.

        Raises:
            RuntimeError: If backup fails.
        """
        try:
            # Create data backup directory
            data_backup = backup_dir / "data"
            self.fs.mkdir(data_backup, parents=True, exist_ok=True)

            # Backup each container's volumes
            for container in service.containers:
                # Get container info
                inspect = self.service_manager.run_command(
                    f"docker inspect {container.name}",
                )
                if not inspect:
                    continue

                try:
                    inspect_data = self.json.loads(inspect)[0]
                except (self.json.JSONDecodeError, IndexError):
                    continue

                # Copy volume data
                for mount in inspect_data.get("Mounts", []):
                    if mount["Type"] != "volume":
                        continue

                    volume_name = mount["Name"]
                    volume_path = data_backup / volume_name
                    self.fs.mkdir(volume_path, parents=True, exist_ok=True)

                    # Copy volume contents
                    source_path = mount["Source"]
                    if self.fs.exists(Path(source_path)):
                        self.fs.copytree(Path(source_path), volume_path, dirs_exist_ok=True)
        except Exception as e:
            self.logger.exception(f"Failed to backup data volumes: {str(e)}")
            raise RuntimeError(f"Failed to backup data volumes: {str(e)}") from e

    def _restore_config(self, service: Service, backup_dir: Path) -> None:
        """Restore service configuration from backup.

        Args:
            service: Service to restore.
            backup_dir: Directory containing backup.

        Raises:
            RuntimeError: If restore fails.
        """
        try:
            config_backup = backup_dir / "config"
            if self.fs.exists(config_backup):
                # Ensure config directory exists
                self.fs.mkdir(service.config_path, parents=True, exist_ok=True)

                # Copy config files
                for item in self.fs.iterdir(config_backup):
                    item_path = Path(item)
                    if self.fs.is_file(item_path):
                        self.fs.copy2(item_path, service.config_path)
                    else:
                        self.fs.copytree(
                            item_path, service.config_path / item_path.name, dirs_exist_ok=True
                        )
        except Exception as e:
            self.logger.exception(f"Failed to restore config: {str(e)}")
            raise RuntimeError(f"Failed to restore config: {str(e)}") from e

    def _restore_data_volumes(self, service: Service, backup_dir: Path) -> None:
        """Restore service data volumes from backup.

        Args:
            service: Service to restore.
            backup_dir: Directory containing backup.

        Raises:
            RuntimeError: If restore fails.
        """
        try:
            data_backup = backup_dir / "data"
            if not self.fs.exists(data_backup):
                return

            # Restore each volume
            for volume_backup in self.fs.iterdir(data_backup):
                volume_backup_path = Path(volume_backup)
                if not self.fs.is_dir(volume_backup_path):
                    continue

                volume_name = volume_backup_path.name

                # Recreate volume
                self.service_manager.run_command(f"docker volume rm -f {volume_name}")
                self.service_manager.run_command(f"docker volume create {volume_name}")

                # Get volume mount point
                inspect = self.service_manager.run_command(
                    f"docker volume inspect {volume_name}",
                )
                try:
                    mount_point = self.json.loads(inspect)[0]["Mountpoint"]
                except (self.json.JSONDecodeError, IndexError, KeyError):
                    continue

                # Copy data to volume
                mount_path = Path(mount_point)
                if self.fs.exists(mount_path):
                    self.fs.copytree(volume_backup_path, mount_path, dirs_exist_ok=True)
        except Exception as e:
            self.logger.exception(f"Failed to restore data volumes: {str(e)}")
            raise RuntimeError(f"Failed to restore data volumes: {str(e)}") from e

    def _sync_config_to_remote(self, service: Service) -> None:
        """Sync local configuration to remote host.

        Args:
            service: Service to sync configuration for.
        """
        self.service_manager.run_command(f"mkdir -p {service.path}")

        compose_path = service.config_path / "docker-compose.yml"
        if self.fs.exists(compose_path):
            remote_path = service.path / "docker-compose.yml"
            compose_content = self.fs.read_text(compose_path)
            self.service_manager.run_command(
                f"cat > {remote_path} << 'EOL'\n{compose_content}\nEOL",
            )

