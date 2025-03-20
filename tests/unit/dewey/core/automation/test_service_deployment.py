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
from dewey.core.automation.service_deployment import ServiceDeployment
from dewey.core.base_script import BaseScript


@pytest.fixture
def mock_base_script() -> MagicMock:
    """Mock BaseScript instance."""
    mock_script = MagicMock(spec=BaseScript)
    mock_script.get_config_value.return_value = "test_value"
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
    mock_service_manager = MagicMock()
    mock_service_manager.run_command.return_value = ""
    return mock_service_manager


@pytest.fixture
def service_deployment() -> ServiceDeployment:
    """Create a ServiceDeployment instance with mocked BaseScript."""
    with patch("dewey.core.automation.service_deployment.BaseScript.__init__", return_value=None):
        sd = ServiceDeployment()
        sd.logger = MagicMock()
        sd.get_config_value = MagicMock(return_value="/tmp/dewey")
        sd.workspace_dir = Path("/tmp/dewey/workspace")
        sd.config_dir = Path("/tmp/dewey/config")
        sd.backups_dir = sd.workspace_dir / "backups"
        sd.backups_dir.mkdir(parents=True, exist_ok=True)
        return sd


@patch("dewey.core.automation.service_deployment.BaseScript.__init__", return_value=None)
def test_service_deployment_init(mock_init: MagicMock) -> None:
    """Test that ServiceDeployment initializes correctly."""
    sd = ServiceDeployment()
    assert sd.name == "service_deployment"
    assert sd.description == "Service deployment and configuration management"
    assert sd.config_section == "service_deployment"
    assert sd.requires_db is False
    assert sd.enable_llm is False
    assert sd.service_manager is None


def test_service_deployment_run(service_deployment: ServiceDeployment, mock_service_manager: MagicMock) -> None:
    """Test that ServiceDeployment.run() sets the service_manager attribute."""
    service_deployment.run(mock_service_manager)
    assert service_deployment.service_manager == mock_service_manager


@patch("pathlib.Path.mkdir")
def test_ensure_service_dirs_success(
    mock_mkdir: MagicMock, service_deployment: ServiceDeployment, mock_service: MagicMock
) -> None:
    """Test that _ensure_service_dirs creates directories successfully."""
    service_deployment._ensure_service_dirs(mock_service)
    assert mock_service.path.parent.mkdir.called
    assert mock_service.config_path.parent.mkdir.called
    assert mock_service.path.mkdir.called
    assert mock_service.config_path.mkdir.called


@patch("pathlib.Path.mkdir", side_effect=OSError("Failed to create directory"))
def test_ensure_service_dirs_failure(
    mock_mkdir: MagicMock, service_deployment: ServiceDeployment, mock_service: MagicMock
) -> None:
    """Test that _ensure_service_dirs raises RuntimeError on OSError."""
    with pytest.raises(RuntimeError) as exc_info:
        service_deployment._ensure_service_dirs(mock_service)
    assert "Failed to create service directories" in str(exc_info.value)
    service_deployment.logger.error.assert_called()


@patch("dewey.core.automation.service_deployment.ServiceDeployment._ensure_service_dirs")
@patch("dewey.core.automation.service_deployment.ServiceDeployment._generate_compose_config")
@patch("dewey.core.automation.service_deployment.ServiceDeployment._write_compose_config")
@patch("dewey.core.automation.service_deployment.ServiceDeployment._start_service")
def test_deploy_service_success(
    mock_start_service: MagicMock,
    mock_write_compose_config: MagicMock,
    mock_generate_compose_config: MagicMock,
    mock_ensure_service_dirs: MagicMock,
    service_deployment: ServiceDeployment,
    mock_service: MagicMock,
) -> None:
    """Test that deploy_service calls all the necessary methods on success."""
    config = {"services": {"web": {"image": "nginx"}}}
    service_deployment.deploy_service(mock_service, config)

    mock_ensure_service_dirs.assert_called_once_with(mock_service)
    mock_generate_compose_config.assert_called_once_with(config)
    mock_write_compose_config.assert_called_once_with(mock_service, mock_generate_compose_config.return_value)
    mock_start_service.assert_called_once_with(mock_service)
    assert not service_deployment.logger.exception.called


@patch("dewey.core.automation.service_deployment.ServiceDeployment._ensure_service_dirs", side_effect=Exception("Failed"))
def test_deploy_service_failure(
    mock_ensure_service_dirs: MagicMock,
    service_deployment: ServiceDeployment,
    mock_service: MagicMock,
) -> None:
    """Test that deploy_service raises RuntimeError on failure."""
    config = {"services": {"web": {"image": "nginx"}}}
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


@patch("pathlib.Path.write_text")
def test_write_compose_config(
    mock_write_text: MagicMock, service_deployment: ServiceDeployment, mock_service: MagicMock
) -> None:
    """Test that _write_compose_config writes the config to file."""
    config = {"version": "3", "services": {"web": {"image": "nginx"}}}
    service_deployment._write_compose_config(mock_service, config)
    mock_write_text.assert_called_once_with(json.dumps(config, indent=2))


@patch("shutil.make_archive")
@patch("datetime.datetime")
def test_create_archive_success(
    mock_datetime: MagicMock,
    mock_make_archive: MagicMock,
    service_deployment: ServiceDeployment,
    mock_service: MagicMock,
) -> None:
    """Test that _create_archive creates an archive successfully."""
    mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
    backup_dir = Path("/tmp/backup_dir")
    archive_path = service_deployment._create_archive(mock_service, backup_dir)

    assert archive_path == service_deployment.backups_dir / "test_service_backup_20240101_120000.tar.gz"
    mock_make_archive.assert_called_once_with(
        str(service_deployment.backups_dir / "test_service_backup_20240101_120000"),
        "gztar",
        str(backup_dir),
    )


@patch("shutil.make_archive", side_effect=Exception("Failed to create archive"))
@patch("datetime.datetime")
def test_create_archive_failure(
    mock_datetime: MagicMock,
    mock_make_archive: MagicMock,
    service_deployment: ServiceDeployment,
    mock_service: MagicMock,
) -> None:
    """Test that _create_archive raises RuntimeError on failure."""
    mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
    backup_dir = Path("/tmp/backup_dir")
    with pytest.raises(RuntimeError) as exc_info:
        service_deployment._create_archive(mock_service, backup_dir)
    assert "Failed to create archive" in str(exc_info.value)
    service_deployment.logger.exception.assert_called()


@patch("tempfile.TemporaryDirectory")
@patch("dewey.core.automation.service_deployment.ServiceDeployment._backup_config")
@patch("dewey.core.automation.service_deployment.ServiceDeployment._backup_data_volumes")
@patch("dewey.core.automation.service_deployment.ServiceDeployment._create_archive")
def test_backup_service_success(
    mock_create_archive: MagicMock,
    mock_backup_data_volumes: MagicMock,
    mock_backup_config: MagicMock,
    mock_temporary_directory: MagicMock,
    service_deployment: ServiceDeployment,
    mock_service: MagicMock,
) -> None:
    """Test that backup_service calls all the necessary methods on success."""
    mock_temporary_directory.return_value.__enter__.return_value = "/tmp/temp_dir"
    backup_path = service_deployment.backup_service(mock_service)

    mock_backup_config.assert_called_once_with(mock_service, Path("/tmp/temp_dir"))
    mock_backup_data_volumes.assert_called_once_with(mock_service, Path("/tmp/temp_dir"))
    mock_create_archive.assert_called_once_with(mock_service, Path("/tmp/temp_dir"))
    assert backup_path == mock_create_archive.return_value
    assert not service_deployment.logger.exception.called


@patch("tempfile.TemporaryDirectory")
@patch("dewey.core.automation.service_deployment.ServiceDeployment._backup_config", side_effect=Exception("Failed"))
def test_backup_service_failure(
    mock_backup_config: MagicMock,
    mock_temporary_directory: MagicMock,
    service_deployment: ServiceDeployment,
    mock_service: MagicMock,
) -> None:
    """Test that backup_service raises RuntimeError on failure."""
    mock_temporary_directory.return_value.__enter__.return_value = "/tmp/temp_dir"
    with pytest.raises(RuntimeError) as exc_info:
        service_deployment.backup_service(mock_service)
    assert "Service backup failed" in str(exc_info.value)
    service_deployment.logger.exception.assert_called_once()


@patch("pathlib.Path.exists", return_value=False)
def test_restore_service_file_not_found(
    mock_exists: MagicMock, service_deployment: ServiceDeployment, mock_service: MagicMock
) -> None:
    """Test that restore_service raises FileNotFoundError if backup file doesn't exist."""
    backup_path = Path("/tmp/backup.tar.gz")
    with pytest.raises(FileNotFoundError) as exc_info:
        service_deployment.restore_service(mock_service, backup_path)
    assert "Backup file not found" in str(exc_info.value)
    service_deployment.logger.error.assert_called()


@patch("pathlib.Path.exists", return_value=True)
@patch("tempfile.TemporaryDirectory")
@patch("dewey.core.automation.service_deployment.ServiceDeployment._ensure_service_dirs")
@patch("dewey.core.automation.service_deployment.ServiceDeployment._stop_service")
@patch("shutil.unpack_archive")
@patch("dewey.core.automation.service_deployment.ServiceDeployment._restore_config")
@patch("dewey.core.automation.service_deployment.ServiceDeployment._restore_data_volumes")
@patch("dewey.core.automation.service_deployment.ServiceDeployment._start_service")
def test_restore_service_success(
    mock_start_service: MagicMock,
    mock_restore_data_volumes: MagicMock,
    mock_restore_config: MagicMock,
    mock_unpack_archive: MagicMock,
    mock_stop_service: MagicMock,
    mock_ensure_service_dirs: MagicMock,
    mock_temporary_directory: MagicMock,
    mock_exists: MagicMock,
    service_deployment: ServiceDeployment,
    mock_service: MagicMock,
) -> None:
    """Test that restore_service calls all the necessary methods on success."""
    mock_temporary_directory.return_value.__enter__.return_value = "/tmp/temp_dir"
    backup_path = Path("/tmp/backup.tar.gz")
    service_deployment.restore_service(mock_service, backup_path)

    mock_ensure_service_dirs.assert_called_once_with(mock_service)
    mock_stop_service.assert_called_once_with(mock_service)
    mock_unpack_archive.assert_called_once_with(str(backup_path), str(Path("/tmp/temp_dir")))
    mock_restore_config.assert_called_once_with(mock_service, Path("/tmp/temp_dir"))
    mock_restore_data_volumes.assert_called_once_with(mock_service, Path("/tmp/temp_dir"))
    mock_start_service.assert_called_once_with(mock_service)
    assert not service_deployment.logger.exception.called


@patch("pathlib.Path.exists", return_value=True)
@patch("tempfile.TemporaryDirectory")
@patch("dewey.core.automation.service_deployment.ServiceDeployment._stop_service", side_effect=Exception("Failed"))
def test_restore_service_failure(
    mock_stop_service: MagicMock,
    mock_temporary_directory: MagicMock,
    mock_exists: MagicMock,
    service_deployment: ServiceDeployment,
    mock_service: MagicMock,
) -> None:
    """Test that restore_service raises RuntimeError on failure."""
    mock_temporary_directory.return_value.__enter__.return_value = "/tmp/temp_dir"
    backup_path = Path("/tmp/backup.tar.gz")
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


@patch("pathlib.Path.mkdir")
@patch("shutil.copytree")
def test_backup_config_success(
    mock_copytree: MagicMock,
    mock_mkdir: MagicMock,
    service_deployment: ServiceDeployment,
    mock_service: MagicMock,
) -> None:
    """Test that _backup_config backs up the config successfully."""
    mock_service.config_path.exists.return_value = True
    backup_dir = Path("/tmp/backup_dir")
    service_deployment._backup_config(mock_service, backup_dir)

    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    mock_copytree.assert_called_once_with(mock_service.config_path, backup_dir / "config", dirs_exist_ok=True)
    assert not service_deployment.logger.exception.called


@patch("pathlib.Path.mkdir")
@patch("shutil.copytree", side_effect=Exception("Failed to copy"))
def test_backup_config_failure(
    mock_copytree: MagicMock,
    mock_mkdir: MagicMock,
    service_deployment: ServiceDeployment,
    mock_service: MagicMock,
) -> None:
    """Test that _backup_config raises RuntimeError on failure."""
    mock_service.config_path.exists.return_value = True
    backup_dir = Path("/tmp/backup_dir")
    with pytest.raises(RuntimeError) as exc_info:
        service_deployment._backup_config(mock_service, backup_dir)
    assert "Failed to backup config" in str(exc_info.value)
    service_deployment.logger.exception.assert_called()


@patch("pathlib.Path.mkdir")
@patch("dewey.core.automation.service_deployment.ServiceDeployment.service_manager.run_command")
@patch("json.loads")
@patch("pathlib.Path.exists")
@patch("shutil.copytree")
def test_backup_data_volumes_success(
    mock_copytree: MagicMock,
    mock_path_exists: MagicMock,
    mock_json_loads: MagicMock,
    mock_run_command: MagicMock,
    mock_mkdir: MagicMock,
    service_deployment: ServiceDeployment,
    mock_service: MagicMock,
) -> None:
    """Test that _backup_data_volumes backs up data volumes successfully."""
    mock_service.containers = [MagicMock(name="container1")]
    mock_run_command.return_value = '[{"Mounts": [{"Type": "volume", "Name": "volume1", "Source": "/tmp/volume1"}]}]'
    mock_json_loads.return_value = [{"Mounts": [{"Type": "volume", "Name": "volume1", "Source": "/tmp/volume1"}]}]
    mock_path_exists.return_value = True

    backup_dir = Path("/tmp/backup_dir")
    service_deployment._backup_data_volumes(mock_service, backup_dir)

    mock_mkdir.assert_called()
    mock_run_command.assert_called_with("docker inspect container1")
    mock_copytree.assert_called_with("/tmp/volume1", backup_dir / "data" / "volume1", dirs_exist_ok=True)
    assert not service_deployment.logger.exception.called


@patch("pathlib.Path.mkdir")
@patch("dewey.core.automation.service_deployment.ServiceDeployment.service_manager.run_command")
@patch("json.loads", side_effect=json.JSONDecodeError("msg", "doc", 0))
def test_backup_data_volumes_json_error(
    mock_json_loads: MagicMock,
    mock_run_command: MagicMock,
    mock_mkdir: MagicMock,
    service_deployment: ServiceDeployment,
    mock_service: MagicMock,
) -> None:
    """Test that _backup_data_volumes handles JSONDecodeError."""
    mock_service.containers = [MagicMock(name="container1")]
    mock_run_command.return_value = 'invalid json'

    backup_dir = Path("/tmp/backup_dir")
    service_deployment._backup_data_volumes(mock_service, backup_dir)

    mock_mkdir.assert_called()
    mock_run_command.assert_called_with("docker inspect container1")
    assert not service_deployment.logger.exception.called


@patch("pathlib.Path.mkdir")
@patch("dewey.core.automation.service_deployment.ServiceDeployment.service_manager.run_command")
@patch("json.loads")
@patch("pathlib.Path.exists")
@patch("shutil.copytree", side_effect=Exception("Failed to copy"))
def test_backup_data_volumes_failure(
    mock_copytree: MagicMock,
    mock_path_exists: MagicMock,
    mock_json_loads: MagicMock,
    mock_run_command: MagicMock,
    mock_mkdir: MagicMock,
    service_deployment: ServiceDeployment,
    mock_service: MagicMock,
) -> None:
    """Test that _backup_data_volumes raises RuntimeError on failure."""
    mock_service.containers = [MagicMock(name="container1")]
    mock_run_command.return_value = '[{"Mounts": [{"Type": "volume", "Name": "volume1", "Source": "/tmp/volume1"}]}]'
    mock_json_loads.return_value = [{"Mounts": [{"Type": "volume", "Name": "volume1", "Source": "/tmp/volume1"}]}]
    mock_path_exists.return_value = True

    backup_dir = Path("/tmp/backup_dir")
    with pytest.raises(RuntimeError) as exc_info:
        service_deployment._backup_data_volumes(mock_service, backup_dir)
    assert "Failed to backup data volumes" in str(exc_info.value)
    service_deployment.logger.exception.assert_called()


@patch("pathlib.Path.exists")
@patch("pathlib.Path.mkdir")
@patch("shutil.copy2")
@patch("shutil.copytree")
def test_restore_config_success(
    mock_copytree: MagicMock,
    mock_copy2: MagicMock,
    mock_mkdir: MagicMock,
    mock_path_exists: MagicMock,
    service_deployment: ServiceDeployment,
    mock_service: MagicMock,
) -> None:
    """Test that _restore_config restores the config successfully."""
    backup_dir = Path("/tmp/backup_dir")
    config_backup = backup_dir / "config"
    config_backup.mkdir(parents=True, exist_ok=True)

    # Create dummy files and directories in the backup
    (config_backup / "file1.txt").write_text("test")
    (config_backup / "dir1").mkdir(exist_ok=True)
    (config_backup / "dir1" / "file2.txt").write_text("test")

    mock_path_exists.return_value = True
    mock_service.config_path.exists.return_value = False

    service_deployment._restore_config(mock_service, backup_dir)

    assert mock_mkdir.called
    assert mock_copy2.called
    assert mock_copytree.called
    assert not service_deployment.logger.exception.called


@patch("pathlib.Path.exists")
@patch("pathlib.Path.mkdir")
@patch("shutil.copy2")
@patch("shutil.copytree", side_effect=Exception("Failed to copy"))
def test_restore_config_failure(
    mock_copytree: MagicMock,
    mock_copy2: MagicMock,
    mock_mkdir: MagicMock,
    mock_path_exists: MagicMock,
    service_deployment: ServiceDeployment,
    mock_service: MagicMock,
) -> None:
    """Test that _restore_config raises RuntimeError on failure."""
    backup_dir = Path("/tmp/backup_dir")
    config_backup = backup_dir / "config"
    config_backup.mkdir(parents=True, exist_ok=True)
    (config_backup / "file1.txt").write_text("test")

    mock_path_exists.return_value = True
    mock_service.config_path.exists.return_value = False

    with pytest.raises(RuntimeError) as exc_info:
        service_deployment._restore_config(mock_service, backup_dir)
    assert "Failed to restore config" in str(exc_info.value)
    service_deployment.logger.exception.assert_called()


@patch("pathlib.Path.exists")
@patch("dewey.core.automation.service_deployment.ServiceDeployment.service_manager.run_command")
@patch("json.loads")
@patch("shutil.copytree")
def test_restore_data_volumes_success(
    mock_copytree: MagicMock,
    mock_json_loads: MagicMock,
    mock_run_command: MagicMock,
    mock_path_exists: MagicMock,
    service_deployment: ServiceDeployment,
    mock_service: MagicMock,
) -> None:
    """Test that _restore_data_volumes restores data volumes successfully."""
    backup_dir = Path("/tmp/backup_dir")
    data_backup = backup_dir / "data"
    data_backup.mkdir(parents=True, exist_ok=True)
    (data_backup / "volume1").mkdir(exist_ok=True)
    (data_backup / "volume1" / "file1.txt").write_text("test")

    mock_path_exists.side_effect = [True, True]  # data_backup.exists(), mount_path.exists()
    mock_run_command.return_value = '[{"Mountpoint": "/var/lib/docker/volumes/volume1/_data"}]'
    mock_json_loads.return_value = [{"Mountpoint": "/var/lib/docker/volumes/volume1/_data"}]

    service_deployment._restore_data_volumes(mock_service, backup_dir)

    assert mock_run_command.call_count == 2
    assert mock_copytree.called
    assert not service_deployment.logger.exception.called


@patch("pathlib.Path.exists")
def test_restore_data_volumes_no_data_backup(
    mock_path_exists: MagicMock, service_deployment: ServiceDeployment, mock_service: MagicMock
) -> None:
    """Test that _restore_data_volumes returns early if data backup doesn't exist."""
    backup_dir = Path("/tmp/backup_dir")
    mock_path_exists.return_value = False
    service_deployment._restore_data_volumes(mock_service, backup_dir)
    assert not service_deployment.logger.exception.called


@patch("pathlib.Path.exists")
@patch("dewey.core.automation.service_deployment.ServiceDeployment.service_manager.run_command")
@patch("json.loads")
@patch("shutil.copytree", side_effect=Exception("Failed to copy"))
def test_restore_data_volumes_failure(
    mock_copytree: MagicMock,
    mock_json_loads: MagicMock,
    mock_run_command: MagicMock,
    mock_path_exists: MagicMock,
    service_deployment: ServiceDeployment,
    mock_service: MagicMock,
) -> None:
    """Test that _restore_data_volumes raises RuntimeError on failure."""
    backup_dir = Path("/tmp/backup_dir")
    data_backup = backup_dir / "data"
    data_backup.mkdir(parents=True, exist_ok=True)
    (data_backup / "volume1").mkdir(exist_ok=True)
    (data_backup / "volume1" / "file1.txt").write_text("test")

    mock_path_exists.side_effect = [True, True]  # data_backup.exists(), mount_path.exists()
    mock_run_command.return_value = '[{"Mountpoint": "/var/lib/docker/volumes/volume1/_data"}]'
    mock_json_loads.return_value = [{"Mountpoint": "/var/lib/docker/volumes/volume1/_data"}]

    with pytest.raises(RuntimeError) as exc_info:
        service_deployment._restore_data_volumes(mock_service, backup_dir)
    assert "Failed to restore data volumes" in str(exc_info.value)
    service_deployment.logger.exception.assert_called()


@patch("dewey.core.automation.service_deployment.ServiceDeployment.service_manager.run_command")
@patch("pathlib.Path.exists", return_value=True)
@patch("pathlib.Path.read_text", return_value="compose content")
def test_sync_config_to_remote_success(
    mock_read_text: MagicMock,
    mock_path_exists: MagicMock,
    mock_run_command: MagicMock,
    service_deployment: ServiceDeployment,
    mock_service: MagicMock,
) -> None:
    """Test that _sync_config_to_remote syncs config to remote successfully."""
    mock_service.config_path = Path("/tmp/test_service/config")
    compose_path = mock_service.config_path / "docker-compose.yml"
    remote_path = mock_service.path / "docker-compose.yml"

    service_deployment._sync_config_to_remote(mock_service)

    mock_run_command.assert_called_with(f"cat > {remote_path} << 'EOL'\ncompose content\nEOL")


@patch("dewey.core.automation.service_deployment.ServiceDeployment.service_manager.run_command")
@patch("pathlib.Path.exists", return_value=False)
def test_sync_config_to_remote_no_compose_file(
    mock_path_exists: MagicMock,
    mock_run_command: MagicMock,
    service_deployment: ServiceDeployment,
    mock_service: MagicMock,
) -> None:
    """Test that _sync_config_to_remote does nothing if compose file doesn't exist."""
    service_deployment._sync_config_to_remote(mock_service)
    assert not mock_run_command.called
