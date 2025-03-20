"""Tests for dewey.core.automation.service_deployment."""

import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch, mock_open

import pytest

from dewey.core.automation.models import Service
from dewey.core.automation.service_deployment import (
    ServiceDeployment,
    ServiceManagerInterface,
    FileSystemInterface,
    RealFileSystem,
)
from dewey.core.base_script import BaseScript


@pytest.fixture
def mock_base_script() -> MagicMock:
    """Mock BaseScript instance."""
    mock_script = MagicMock(spec=BaseScript)
    mock_script.get_config_value.return_value = "/tmp/dewey"  # Set a default config value
    mock_script.logger = MagicMock()
    return mock_script


@pytest.fixture
def mock_service() -> MagicMock:
    """Mock Service instance."""
    mock_service = MagicMock(spec=Service)
    mock_service.name = "test_service"
    mock_service.path = Path("/tmp/test_service")
    mock_service.config_path = Path("/tmp/test_service/config")
    mock_service.containers = []
    return mock_service


@pytest.fixture
def mock_service_manager() -> MagicMock:
    """Mock ServiceManager instance."""
    mock_service_manager = MagicMock(spec=ServiceManagerInterface)
    mock_service_manager.run_command.return_value = ""
    return mock_service_manager


@pytest.fixture
def mock_fs() -> MagicMock:
    """Mock FileSystemInterface instance."""
    mock_fs = MagicMock(spec=FileSystemInterface)
    mock_fs.exists.return_value = True  # Default to True for existence checks
    mock_fs.is_file.return_value = False  # Default to not a file
    mock_fs.is_dir.return_value = True  # Default to a directory
    return mock_fs


@pytest.fixture
def service_deployment(mock_base_script: MagicMock, mock_service_manager: MagicMock, mock_fs: MagicMock) -> ServiceDeployment:
    """Create a ServiceDeployment instance with mocked dependencies."""
    with patch("dewey.core.automation.service_deployment.BaseScript.__init__", return_value=None):
        sd = ServiceDeployment(mock_service_manager, mock_fs)
        sd.logger = mock_base_script.logger
        sd.get_config_value = mock_base_script.get_config_value
        sd.workspace_dir = Path("/tmp/dewey/workspace")
        sd.config_dir = Path("/tmp/dewey/config")
        sd.backups_dir = sd.workspace_dir / "backups"
        return sd


@patch("dewey.core.automation.service_deployment.BaseScript.__init__", return_value=None)
def test_service_deployment_init(mock_init: MagicMock, mock_service_manager: MagicMock, mock_fs: MagicMock) -> None:
    """Test that ServiceDeployment initializes correctly."""
    sd = ServiceDeployment(mock_service_manager, mock_fs)
    assert sd.name == "service_deployment"
    assert sd.description == "Service deployment and configuration management"
    assert sd.config_section == "service_deployment"
    assert sd.requires_db is False
    assert sd.enable_llm is False
    assert sd.service_manager == mock_service_manager
    mock_fs.mkdir.assert_called_once_with(sd.backups_dir, parents=True, exist_ok=True)


def test_service_deployment_run(service_deployment: ServiceDeployment, mock_service_manager: MagicMock) -> None:
    """Test that ServiceDeployment.run() does nothing (as per the code)."""
    service_deployment.run(mock_service_manager)
    # Assert that nothing happens in run
    assert True  # Placeholder assertion


def test_ensure_service_dirs_success(
    service_deployment: ServiceDeployment, mock_service: MagicMock, mock_fs: MagicMock
) -> None:
    """Test that _ensure_service_dirs creates directories successfully."""
    service_deployment._ensure_service_dirs(mock_service)
    mock_fs.mkdir.assert_any_call(mock_service.path.parent, parents=True, exist_ok=True)
    mock_fs.mkdir.assert_any_call(mock_service.config_path.parent, parents=True, exist_ok=True)
    mock_fs.mkdir.assert_any_call(mock_service.path, exist_ok=True)
    mock_fs.mkdir.assert_any_call(mock_service.config_path, exist_ok=True)


def test_ensure_service_dirs_failure(
    service_deployment: ServiceDeployment, mock_service: MagicMock, mock_fs: MagicMock
) -> None:
    """Test that _ensure_service_dirs raises RuntimeError on OSError."""
    mock_fs.mkdir.side_effect = OSError("Failed to create directory")
    with pytest.raises(RuntimeError) as exc_info:
        service_deployment._ensure_service_dirs(mock_service)
    assert "Failed to create service directories" in str(exc_info.value)
    service_deployment.logger.error.assert_called()


def test_deploy_service_success(
    service_deployment: ServiceDeployment,
    mock_service: MagicMock,
    mock_service_manager: MagicMock,
    mock_fs: MagicMock,
) -> None:
    """Test that deploy_service calls all the necessary methods on success."""
    config = {"services": {"web": {"image": "nginx"}}}
    with patch.object(service_deployment, "_ensure_service_dirs") as mock_ensure_service_dirs, \
         patch.object(service_deployment, "_generate_compose_config") as mock_generate_compose_config, \
         patch.object(service_deployment, "_write_compose_config") as mock_write_compose_config, \
         patch.object(service_deployment, "_start_service") as mock_start_service:

        service_deployment.deploy_service(mock_service, config)

        mock_ensure_service_dirs.assert_called_once_with(mock_service)
        mock_generate_compose_config.assert_called_once_with(config)
        mock_write_compose_config.assert_called_once_with(mock_service, mock_generate_compose_config.return_value)
        mock_start_service.assert_called_once_with(mock_service)
        assert not service_deployment.logger.exception.called


def test_deploy_service_failure(
    service_deployment: ServiceDeployment,
    mock_service: MagicMock,
    mock_service_manager: MagicMock,
    mock_fs: MagicMock,
) -> None:
    """Test that deploy_service raises RuntimeError on failure."""
    config = {"services": {"web": {"image": "nginx"}}}
    with patch.object(service_deployment, "_ensure_service_dirs", side_effect=Exception("Failed")) as mock_ensure_service_dirs:
        with pytest.raises(RuntimeError) as exc_info:
            service_deployment.deploy_service(mock_service, config)

        assert "Deployment failed" in str(exc_info.value)
        service_deployment.logger.exception.assert_called_once()


def test_generate_compose_config_success(service_deployment: ServiceDeployment) -> None:
    """Test that _generate_compose_config generates a valid compose config."""
    config = {
        "services": {
            "web": {
                "image": "nginx",
                "container_name": "my_web",
                "restart": "always",
                "environment": {"VAR1": "value1"},
                "volumes": ["/data:/var/www/html"],
                "ports": ["80:80"],
                "depends_on": ["db"],
                "healthcheck": {"test": ["CMD", "curl", "-f", "http://localhost"]},
            },
            "db": {"image": "postgres"},
        },
        "networks": {"default": {"driver": "bridge"}},
        "volumes": {"data": {}},
    }

    expected_compose_config = {
        "version": "3",
        "services": {
            "web": {
                "image": "nginx",
                "container_name": "my_web",
                "restart": "always",
                "environment": {"VAR1": "value1"},
                "volumes": ["/data:/var/www/html"],
                "ports": ["80:80"],
                "depends_on": ["db"],
                "healthcheck": {"test": ["CMD", "curl", "-f", "http://localhost"]},
            },
            "db": {"image": "postgres", "container_name": "db", "restart": "unless-stopped"},
        },
        "networks": {"default": {"driver": "bridge"}},
        "volumes": {"data": {}},
    }

    compose_config = service_deployment._generate_compose_config(config)
    assert compose_config == expected_compose_config


def test_generate_compose_config_missing_image(service_deployment: ServiceDeployment) -> None:
    """Test that _generate_compose_config raises KeyError if image is missing."""
    config = {"services": {"web": {"container_name": "my_web"}}}
    with pytest.raises(KeyError) as exc_info:
        service_deployment._generate_compose_config(config)
    assert "Missing required 'image' field for service web" in str(exc_info.value)
    service_deployment.logger.error.assert_called()


def test_write_compose_config(
    service_deployment: ServiceDeployment, mock_service: MagicMock, mock_fs: MagicMock
) -> None:
    """Test that _write_compose_config writes the config to file."""
    config = {"version": "3", "services": {"web": {"image": "nginx"}}}
    service_deployment._write_compose_config(mock_service, config)
    compose_file = mock_service.config_path / "docker-compose.yml"
    mock_fs.write_text.assert_called_once_with(compose_file, json.dumps(config, indent=2))


def test_generate_timestamp(service_deployment: ServiceDeployment) -> None:
    """Test that _generate_timestamp generates a valid timestamp string."""
    with patch("dewey.core.automation.service_deployment.datetime") as mock_datetime:
        mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
        timestamp = service_deployment._generate_timestamp()
        assert timestamp == "20240101_120000"


def test_create_archive_success(
    service_deployment: ServiceDeployment, mock_service: MagicMock, mock_fs: MagicMock
) -> None:
    """Test that _create_archive creates an archive successfully."""
    with patch.object(service_deployment, "_generate_timestamp") as mock_generate_timestamp:
        mock_generate_timestamp.return_value = "20240101_120000"
        backup_dir = Path("/tmp/backup_dir")
        archive_path = service_deployment._create_archive(mock_service, backup_dir)

        assert archive_path == service_deployment.backups_dir / "test_service_backup_20240101_120000.tar.gz"
        mock_fs.make_archive.assert_called_once_with(
            str(service_deployment.backups_dir / "test_service_backup_20240101_120000"),
            "gztar",
            str(backup_dir),
        )


def test_create_archive_failure(
    service_deployment: ServiceDeployment, mock_service: MagicMock, mock_fs: MagicMock
) -> None:
    """Test that _create_archive raises RuntimeError on failure."""
    mock_fs.make_archive.side_effect = Exception("Failed to create archive")
    with patch.object(service_deployment, "_generate_timestamp") as mock_generate_timestamp:
        mock_generate_timestamp.return_value = "20240101_120000"
        backup_dir = Path("/tmp/backup_dir")
        with pytest.raises(RuntimeError) as exc_info:
            service_deployment._create_archive(mock_service, backup_dir)
        assert "Failed to create archive" in str(exc_info.value)
        service_deployment.logger.exception.assert_called()


def test_backup_service_success(
    service_deployment: ServiceDeployment, mock_service: MagicMock, mock_fs: MagicMock
) -> None:
    """Test that backup_service calls all the necessary methods on success."""
    with tempfile.TemporaryDirectory() as temp_dir, \
         patch.object(service_deployment, "_backup_config") as mock_backup_config, \
         patch.object(service_deployment, "_backup_data_volumes") as mock_backup_data_volumes, \
         patch.object(service_deployment, "_create_archive") as mock_create_archive:

        backup_path = service_deployment.backup_service(mock_service)

        mock_backup_config.assert_called_once_with(mock_service, Path(temp_dir))
        mock_backup_data_volumes.assert_called_once_with(mock_service, Path(temp_dir))
        mock_create_archive.assert_called_once_with(mock_service, Path(temp_dir))
        assert backup_path == mock_create_archive.return_value
        assert not service_deployment.logger.exception.called


def test_backup_service_failure(
    service_deployment: ServiceDeployment, mock_service: MagicMock, mock_fs: MagicMock
) -> None:
    """Test that backup_service raises RuntimeError on failure."""
    with tempfile.TemporaryDirectory() as temp_dir, \
         patch.object(service_deployment, "_backup_config", side_effect=Exception("Failed")) as mock_backup_config:
        with pytest.raises(RuntimeError) as exc_info:
            service_deployment.backup_service(mock_service)
        assert "Service backup failed" in str(exc_info.value)
        service_deployment.logger.exception.assert_called_once()


def test_restore_service_file_not_found(
    service_deployment: ServiceDeployment, mock_service: MagicMock, mock_fs: MagicMock
) -> None:
    """Test that restore_service raises FileNotFoundError if backup file doesn't exist."""
    mock_fs.exists.return_value = False
    backup_path = Path("/tmp/backup.tar.gz")
    with pytest.raises(FileNotFoundError) as exc_info:
        service_deployment.restore_service(mock_service, backup_path)
    assert "Backup file not found" in str(exc_info.value)
    service_deployment.logger.error.assert_called()


def test_restore_service_success(
    service_deployment: ServiceDeployment, mock_service: MagicMock, mock_service_manager: MagicMock, mock_fs: MagicMock
) -> None:
    """Test that restore_service calls all the necessary methods on success."""
    backup_path = Path("/tmp/backup.tar.gz")
    with tempfile.TemporaryDirectory() as temp_dir, \
         patch.object(service_deployment, "_ensure_service_dirs") as mock_ensure_service_dirs, \
         patch.object(service_deployment, "_stop_service") as mock_stop_service, \
         patch.object(service_deployment, "_restore_config") as mock_restore_config, \
         patch.object(service_deployment, "_restore_data_volumes") as mock_restore_data_volumes, \
         patch.object(service_deployment, "_start_service") as mock_start_service:

        service_deployment.restore_service(mock_service, backup_path)

        mock_ensure_service_dirs.assert_called_once_with(mock_service)
        mock_stop_service.assert_called_once_with(mock_service)
        mock_fs.unpack_archive.assert_called_once_with(str(backup_path), str(temp_dir))
        mock_restore_config.assert_called_once_with(mock_service, Path(temp_dir))
        mock_restore_data_volumes.assert_called_once_with(mock_service, Path(temp_dir))
        mock_start_service.assert_called_once_with(mock_service)
        assert not service_deployment.logger.exception.called


def test_restore_service_failure(
    service_deployment: ServiceDeployment, mock_service: MagicMock, mock_service_manager: MagicMock, mock_fs: MagicMock
) -> None:
    """Test that restore_service raises RuntimeError on failure."""
    backup_path = Path("/tmp/backup.tar.gz")
    with tempfile.TemporaryDirectory() as temp_dir, \
         patch.object(service_deployment, "_stop_service", side_effect=Exception("Failed")) as mock_stop_service:
        with pytest.raises(RuntimeError) as exc_info:
            service_deployment.restore_service(mock_service, backup_path)
        assert "Service restore failed" in str(exc_info.value)
        service_deployment.logger.exception.assert_called_once()


def test_start_service(
    service_deployment: ServiceDeployment, mock_service: MagicMock, mock_service_manager: MagicMock
) -> None:
    """Test that _start_service calls the service manager with the correct command."""
    service_deployment._start_service(mock_service)
    mock_service_manager.run_command.assert_called_once_with(
        f"cd {mock_service.path} && docker-compose up -d"
    )


def test_stop_service(
    service_deployment: ServiceDeployment, mock_service: MagicMock, mock_service_manager: MagicMock
) -> None:
    """Test that _stop_service calls the service manager with the correct command."""
    service_deployment._stop_service(mock_service)
    mock_service_manager.run_command.assert_called_once_with(f"cd {mock_service.path} && docker-compose down")


def test_backup_config_success(
    service_deployment: ServiceDeployment, mock_service: MagicMock, mock_fs: MagicMock
) -> None:
    """Test that _backup_config backs up the config successfully."""
    backup_dir = Path("/tmp/backup_dir")
    service_deployment._backup_config(mock_service, backup_dir)

    mock_fs.mkdir.assert_called_once_with(backup_dir / "config", parents=True, exist_ok=True)
    mock_fs.copytree.assert_called_once_with(mock_service.config_path, backup_dir / "config", dirs_exist_ok=True)
    assert not service_deployment.logger.exception.called


def test_backup_config_failure(
    service_deployment: ServiceDeployment, mock_service: MagicMock, mock_fs: MagicMock
) -> None:
    """Test that _backup_config raises RuntimeError on failure."""
    mock_fs.copytree.side_effect = Exception("Failed to copy")
    backup_dir = Path("/tmp/backup_dir")
    with pytest.raises(RuntimeError) as exc_info:
        service_deployment._backup_config(mock_service, backup_dir)
    assert "Failed to backup config" in str(exc_info.value)
    service_deployment.logger.exception.assert_called()


def test_backup_data_volumes_success(
    service_deployment: ServiceDeployment, mock_service: MagicMock, mock_service_manager: MagicMock, mock_fs: MagicMock
) -> None:
    """Test that _backup_data_volumes backs up data volumes successfully."""
    mock_service.containers = [MagicMock(name="container1")]
    mock_service_manager.run_command.return_value = '[{"Mounts": [{"Type": "volume", "Name": "volume1", "Source": "/tmp/volume1"}]}]'

    backup_dir = Path("/tmp/backup_dir")
    service_deployment._backup_data_volumes(mock_service, backup_dir)

    mock_fs.mkdir.assert_called_with(backup_dir / "data", parents=True, exist_ok=True)
    mock_service_manager.run_command.assert_called_with("docker inspect container1")
    mock_fs.mkdir.assert_called_with(backup_dir / "data" / "volume1", parents=True, exist_ok=True)
    mock_fs.copytree.assert_called_with(Path("/tmp/volume1"), backup_dir / "data" / "volume1", dirs_exist_ok=True)
    assert not service_deployment.logger.exception.called


def test_backup_data_volumes_json_error(
    service_deployment: ServiceDeployment, mock_service: MagicMock, mock_service_manager: MagicMock
) -> None:
    """Test that _backup_data_volumes handles JSONDecodeError."""
    mock_service.containers = [MagicMock(name="container1")]
    mock_service_manager.run_command.return_value = 'invalid json'

    backup_dir = Path("/tmp/backup_dir")
    service_deployment._backup_data_volumes(mock_service, backup_dir)

    # Assert that it handles the error and continues
    assert not service_deployment.logger.exception.called


def test_backup_data_volumes_failure(
    service_deployment: ServiceDeployment, mock_service: MagicMock, mock_service_manager: MagicMock, mock_fs: MagicMock
) -> None:
    """Test that _backup_data_volumes raises RuntimeError on failure."""
    mock_service.containers = [MagicMock(name="container1")]
    mock_service_manager.run_command.return_value = '[{"Mounts": [{"Type": "volume", "Name": "volume1", "Source": "/tmp/volume1"}]}]'
    mock_fs.copytree.side_effect = Exception("Failed to copy")

    backup_dir = Path("/tmp/backup_dir")
    with pytest.raises(RuntimeError) as exc_info:
        service_deployment._backup_data_volumes(mock_service, backup_dir)
    assert "Failed to backup data volumes" in str(exc_info.value)
    service_deployment.logger.exception.assert_called()


def test_restore_config_success(
    service_deployment: ServiceDeployment, mock_service: MagicMock, mock_fs: MagicMock
) -> None:
    """Test that _restore_config restores the config successfully."""
    backup_dir = Path("/tmp/backup_dir")
    config_backup = backup_dir / "config"

    # Mock the file system to return some files and directories
    mock_fs.iterdir.return_value = [config_backup / "file1.txt", config_backup / "dir1"]
    mock_fs.is_file.side_effect = [True, False]  # file1.txt is a file, dir1 is not
    mock_fs.is_dir.side_effect = [False, True]

    service_deployment._restore_config(mock_service, backup_dir)

    mock_fs.mkdir.assert_called_with(mock_service.config_path, parents=True, exist_ok=True)
    assert mock_fs.copy2.call_count == 1
    assert mock_fs.copytree.call_count == 1
    assert not service_deployment.logger.exception.called


def test_restore_config_failure(
    service_deployment: ServiceDeployment, mock_service: MagicMock, mock_fs: MagicMock
) -> None:
    """Test that _restore_config raises RuntimeError on failure."""
    backup_dir = Path("/tmp/backup_dir")
    config_backup = backup_dir / "config"

    # Mock the file system to return some files and directories
    mock_fs.iterdir.return_value = [config_backup / "file1.txt", config_backup / "dir1"]
    mock_fs.is_file.side_effect = [True, False]  # file1.txt is a file, dir1 is not
    mock_fs.is_dir.side_effect = [False, True]
    mock_fs.copytree.side_effect = Exception("Failed to copy")

    with pytest.raises(RuntimeError) as exc_info:
        service_deployment._restore_config(mock_service, backup_dir)
    assert "Failed to restore config" in str(exc_info.value)
    service_deployment.logger.exception.assert_called()


def test_restore_data_volumes_success(
    service_deployment: ServiceDeployment, mock_service: MagicMock, mock_service_manager: MagicMock, mock_fs: MagicMock
) -> None:
    """Test that _restore_data_volumes restores data volumes successfully."""
    backup_dir = Path("/tmp/backup_dir")
    data_backup = backup_dir / "data"

    # Mock the file system to return some volumes
    mock_fs.iterdir.return_value = [data_backup / "volume1", data_backup / "volume2"]
    mock_fs.is_dir.return_value = True
    mock_service_manager.run_command.return_value = '[{"Mountpoint": "/var/lib/docker/volumes/volume1/_data"}]'

    service_deployment._restore_data_volumes(mock_service, backup_dir)

    assert mock_service_manager.run_command.call_count == 6  # 2 remove, 2 create, 2 inspect
    assert mock_fs.copytree.call_count == 2
    assert not service_deployment.logger.exception.called


def test_restore_data_volumes_no_data_backup(
    service_deployment: ServiceDeployment, mock_service: MagicMock, mock_fs: MagicMock
) -> None:
    """Test that _restore_data_volumes returns early if data backup doesn't exist."""
    mock_fs.exists.return_value = False
    backup_dir = Path("/tmp/backup_dir")
    service_deployment._restore_data_volumes(mock_service, backup_dir)
    assert not service_deployment.logger.exception.called
    assert not service_deployment.logger.exception.called


def test_restore_data_volumes_failure(
    service_deployment: ServiceDeployment, mock_service: MagicMock, mock_service_manager: MagicMock, mock_fs: MagicMock
) -> None:
    """Test that _restore_data_volumes raises RuntimeError on failure."""
    backup_dir = Path("/tmp/backup_dir")
    data_backup = backup_dir / "data"

    # Mock the file system to return some volumes
    mock_fs.iterdir.return_value = [data_backup / "volume1", data_backup / "volume2"]
    mock_fs.is_dir.return_value = True
    mock_service_manager.run_command.return_value = '[{"Mountpoint": "/var/lib/docker/volumes/volume1/_data"}]'
    mock_fs.copytree.side_effect = Exception("Failed to copy")

    with pytest.raises(RuntimeError) as exc_info:
        service_deployment._restore_data_volumes(mock_service, backup_dir)
    assert "Failed to restore data volumes" in str(exc_info.value)
    service_deployment.logger.exception.assert_called()


def test_sync_config_to_remote_success(
    service_deployment: ServiceDeployment, mock_service: MagicMock, mock_service_manager: MagicMock, mock_fs: MagicMock
) -> None:
    """Test that _sync_config_to_remote syncs config to remote successfully."""
    mock_service.config_path = Path("/tmp/test_service/config")
    compose_path = mock_service.config_path / "docker-compose.yml"
    remote_path = mock_service.path / "docker-compose.yml"
    mock_fs.read_text.return_value = "compose content"

    service_deployment._sync_config_to_remote(mock_service)

    mock_service_manager.run_command.assert_called_with(f"mkdir -p {mock_service.path}")
    mock_fs.read_text.assert_called_with(compose_path)
    mock_service_manager.run_command.assert_called_with(f"cat > {remote_path} << 'EOL'\ncompose content\nEOL")


def test_sync_config_to_remote_no_compose_file(
    service_deployment: ServiceDeployment, mock_service: MagicMock, mock_service_manager: MagicMock, mock_fs: MagicMock
) -> None:
    """Test that _sync_config_to_remote does nothing if compose file doesn't exist."""
    mock_fs.exists.return_value = False
    service_deployment._sync_config_to_remote(mock_service)
    mock_service_manager.run_command.assert_called_with(f"mkdir -p {mock_service.path}")
    assert mock_service_manager.run_command.call_count == 1
