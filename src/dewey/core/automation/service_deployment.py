# Refactored from: service_deployment
# Date: 2025-03-16T16:19:08.580204
# Refactor Version: 1.0
import os
import json
import shutil
import tempfile
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dewey.core.base_script import BaseScript
from .models import Service




class ServiceDeployment(BaseScript):
    """Service deployment and configuration management.

    Implements centralized configuration and error handling via BaseScript.

    Attributes:
        service_manager: ServiceManager instance
    """

    def __init__(self) -> None:
        """Initialize ServiceDeployment."""
        super().__init__(
            name="service_deployment",
            description="Service deployment and configuration management",
            config_section="service_deployment"
        )
        self.service_manager = None  # Initialize to None, set in run()
        self.workspace_dir = Path(os.getenv("DEWEY_DIR", os.path.expanduser("~/dewey"))) / "workspace"
        self.config_dir = Path(os.getenv("DEWEY_DIR", os.path.expanduser("~/dewey"))) / "config"
        self.backups_dir = self.workspace_dir / "backups"
        self.backups_dir.mkdir(parents=True, exist_ok=True)

    def run(self, service_manager) -> None:
        """Runs the service deployment process.

        Args:
            service_manager: ServiceManager instance.
        """
        self.service_manager = service_manager

    def _ensure_service_dirs(self, service: Service) -> None:
        """Ensure service directories exist.

        Args:
            service: Service to create directories for.
        """
        try:
            # Create parent directories first
            service.path.parent.mkdir(parents=True, exist_ok=True)
            service.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Then create the actual service directories
            service.path.mkdir(exist_ok=True)
            service.config_path.mkdir(exist_ok=True)
        except OSError as e:
            raise RuntimeError(f"Failed to create service directories: {e}")

    def deploy_service(self, service: Service, config: dict[str, Any]) -> None:
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

    def _generate_compose_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """Generate docker-compose configuration.

        Args:
            config: Service configuration.

        Returns:
            Docker Compose configuration dictionary.
        """
        compose_config = {"version": "3", "services": {}}

        for name, service_config in config.get("services", {}).items():
            if "image" not in service_config:
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
                compose_config["services"][name]["healthcheck"] = service_config["healthcheck"]

        if "networks" in config:
            compose_config["networks"] = config["networks"]

        if "volumes" in config:
            compose_config["volumes"] = config["volumes"]

        return compose_config

    def _write_compose_config(self, service: Service, config: dict[str, Any]) -> None:
        """Write docker-compose configuration to file.

        Args:
            service: Service to write config for.
            config: Docker Compose configuration.
        """
        compose_file = service.config_path / "docker-compose.yml"
        compose_file.write_text(json.dumps(config, indent=2))

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
            self.backups_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate archive name with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"{service.name}_backup_{timestamp}.tar.gz"
            archive_path = self.backups_dir / archive_name
            
            # Create archive
            shutil.make_archive(
                str(archive_path.with_suffix("")),
                "gztar",
                str(backup_dir),
            )
            
            return archive_path
        except Exception as e:
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
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                backup_dir = Path(temp_dir)
                self._ensure_service_dirs(service)
                
                # Stop service and restore from backup
                self._stop_service(service)
                shutil.unpack_archive(str(backup_path), str(backup_dir))
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
            config_backup.mkdir(parents=True, exist_ok=True)
            
            # Copy config if it exists
            if service.config_path.exists():
                shutil.copytree(service.config_path, config_backup, dirs_exist_ok=True)
        except Exception as e:
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
            data_backup.mkdir(parents=True, exist_ok=True)
            
            # Backup each container's volumes
            for container in service.containers:
                # Get container info
                inspect = self.service_manager.run_command(
                    f"docker inspect {container.name}",
                )
                if not inspect:
                    continue
                    
                try:
                    inspect_data = json.loads(inspect)[0]
                except (json.JSONDecodeError, IndexError):
                    continue
                    
                # Copy volume data
                for mount in inspect_data.get("Mounts", []):
                    if mount["Type"] != "volume":
                        continue
                        
                    volume_name = mount["Name"]
                    volume_path = data_backup / volume_name
                    volume_path.mkdir(parents=True, exist_ok=True)
                    
                    # Copy volume contents
                    source_path = mount["Source"]
                    if Path(source_path).exists():
                        shutil.copytree(source_path, volume_path, dirs_exist_ok=True)
        except Exception as e:
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
            if config_backup.exists():
                # Ensure config directory exists
                service.config_path.mkdir(parents=True, exist_ok=True)
                
                # Copy config files
                for item in config_backup.iterdir():
                    if item.is_file():
                        shutil.copy2(item, service.config_path)
                    else:
                        shutil.copytree(item, service.config_path / item.name, dirs_exist_ok=True)
        except Exception as e:
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
            if not data_backup.exists():
                return
                
            # Restore each volume
            for volume_backup in data_backup.iterdir():
                if not volume_backup.is_dir():
                    continue
                    
                volume_name = volume_backup.name
                
                # Recreate volume
                self.service_manager.run_command(f"docker volume rm -f {volume_name}")
                self.service_manager.run_command(f"docker volume create {volume_name}")
                
                # Get volume mount point
                inspect = self.service_manager.run_command(
                    f"docker volume inspect {volume_name}",
                )
                try:
                    mount_point = json.loads(inspect)[0]["Mountpoint"]
                except (json.JSONDecodeError, IndexError, KeyError):
                    continue
                    
                # Copy data to volume
                mount_path = Path(mount_point)
                if mount_path.exists():
                    shutil.copytree(volume_backup, mount_path, dirs_exist_ok=True)
        except Exception as e:
            raise RuntimeError(f"Failed to restore data volumes: {str(e)}") from e

    def _sync_config_to_remote(self, service: Service) -> None:
        """Sync local configuration to remote host.

        Args:
        ----
            service: Service to sync configuration for.

        """
        self.service_manager.run_command(f"mkdir -p {service.path}")

        compose_path = service.config_path / "docker-compose.yml"
        if compose_path.exists():
            remote_path = service.path / "docker-compose.yml"
            compose_content = compose_path.read_text()
            self.service_manager.run_command(
                f"cat > {remote_path} << 'EOL'\n{compose_content}\nEOL",
            )
