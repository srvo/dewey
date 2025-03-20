import pytest
from unittest.mock import MagicMock, patch, call
from pathlib import Path
from dewey.core.automation.service_deployment import ServiceDeployment, Service
from typing import Any
import shutil
import tempfile
import os
from datetime import datetime
import json

@pytest.fixture(autouse=True)
def setup_dewey_dir():
    """Set up DEWEY_DIR environment variable."""
    old_dewey_dir = os.environ.get('DEWEY_DIR')
    os.environ['DEWEY_DIR'] = '/Users/srvo/dewey'
    yield
    if old_dewey_dir:
        os.environ['DEWEY_DIR'] = old_dewey_dir
    else:
        del os.environ['DEWEY_DIR']

@pytest.fixture
def mock_service_manager():
    """Fixture for mocked ServiceManager instance."""
    mock = MagicMock()
    mock.workspace = Path("/workspace")
    mock.config_dir = Path("/config")
    return mock

@pytest.fixture
def service(tmp_path):
    """Fixture for mocked Service instance."""
    service = MagicMock(spec=Service)
    service.name = "test-service"
    service.path = tmp_path / "service"
    service.config_path = tmp_path / "config"
    service.containers = [MagicMock(name="container1")]
    return service

@pytest.fixture
def temp_dir(tmp_path):
    """Fixture for temporary directory."""
    return tmp_path

@pytest.fixture
def deployment(mock_service_manager, tmp_path):
    """Fixture for ServiceDeployment instance."""
    deployment = ServiceDeployment(mock_service_manager)
    deployment.backups_dir = tmp_path / "backups"
    deployment.backups_dir.mkdir(parents=True)
    return deployment

def test_deploy_service_happy_path(mock_service_manager, service):
    """Test successful deployment with valid config."""
    config = {
        "services": {
            "web": {
                "image": "nginx",
                "container_name": "web-container",
                "restart": "always",
                "environment": {"VAR": "value"},
                "volumes": ["/data"],
                "ports": ["80:80"],
                "depends_on": ["db"],
                "healthcheck": {"test": ["CMD", "curl", "-f", "localhost"]}
            }
        },
        "networks": {"default": None},
        "volumes": ["data_volume"]
    }

    deployment = ServiceDeployment(mock_service_manager)
    deployment.deploy_service(service, config)

    # Verify method calls in order
    mock_service_manager.run_command.assert_has_calls([
        call("mkdir -p /service/path"),
        call("cd /service/path && docker-compose up -d")
    ])

    # Verify compose config generation
    compose_config = deployment._generate_compose_config(config)
    assert "nginx" in compose_config["services"]["web"]["image"]

def test_backup_service_happy_path(mock_service_manager, service, temp_dir, monkeypatch):
    """Test backup creation with config and data volumes."""
    monkeypatch.setattr(tempfile, 'TemporaryDirectory', lambda: temp_dir)
    deployment = ServiceDeployment(mock_service_manager)
    backup_path = deployment.backup_service(service)

    # Verify backup structure
    assert backup_path.exists()
    assert (temp_dir / "config").is_dir()
    assert (temp_dir / "data/container1").is_dir()

    # Verify docker commands for volume backup
    mock_service_manager.run_command.assert_any_call(
        "docker run --rm -v container1:/source -v /tmp/backup/data/container1:/backup alpine cp -r /source/. /backup/"
    )

def test_restore_service_happy_path(mock_service_manager, service, temp_dir):
    """Test service restore from backup archive."""
    backup_path = temp_dir / "test_backup.tar.gz"
    backup_path.touch()

    deployment = ServiceDeployment(mock_service_manager)
    deployment.restore_service(service, backup_path)

    # Verify restore steps
    mock_service_manager.run_command.assert_has_calls([
        call("cd /service/path && docker-compose down"),
        call("docker volume rm -f some_volume"),
        call("docker volume create some_volume"),
        call("cd /service/path && docker-compose up -d")
    ])

def test_backup_no_volumes(mock_service_manager, service):
    """Test backup when no data volumes exist."""
    service.containers = []
    deployment = ServiceDeployment(mock_service_manager)
    deployment.backup_service(service)

    # Verify no docker commands for volumes were executed
    mock_service_manager.run_command.assert_not_called()

def test_invalid_compose_config(mock_service_manager):
    """Test config validation for missing required fields."""
    deployment = ServiceDeployment(mock_service_manager)
    invalid_config = {"services": {"web": {}}}

    with pytest.raises(KeyError):
        deployment._generate_compose_config(invalid_config)

def test_restore_missing_backup_dir(mock_service_manager, service, temp_dir):
    """Test restore when backup directory is missing."""
    deployment = ServiceDeployment(mock_service_manager)
    backup_path = temp_dir / "missing.tar.gz"

    with pytest.raises(FileNotFoundError):
        deployment.restore_service(service, backup_path)

@pytest.mark.parametrize("timestamp", ["20250317_120000"])
@patch("datetime.datetime")
def test_create_archive(mock_datetime, timestamp, deployment, service, tmp_path):
    """Test archive naming and creation."""
    # Configure mock datetime
    mock_now = MagicMock()
    mock_now.strftime.return_value = timestamp
    mock_datetime.now.return_value = mock_now
    
    # Create test backup directory
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir(parents=True)
    (backup_dir / "test.txt").write_text("test")
    
    # Create archive
    archive_path = deployment._create_archive(service, backup_dir)
    expected_path = deployment.backups_dir / f"test-service_backup_{timestamp}.tar.gz"
    
    assert archive_path == expected_path
    assert archive_path.exists()

def test_sync_config_to_remote(mock_service_manager, service):
    """Test remote config synchronization."""
    compose_content = "version: '3'"
    (service.config_path / "docker-compose.yml").write_text(compose_content)
    deployment = ServiceDeployment(mock_service_manager)
    deployment._sync_config_to_remote(service)

    # Verify remote path creation and file content
    mock_service_manager.run_command.assert_any_call(
        f"cat > /service/path/docker-compose.yml << 'EOL'\n{compose_content}\nEOL"
    )

# Add new test cases and fixtures for comprehensive coverage

@pytest.fixture
def service_manager():
    """Mock ServiceManager with controlled command execution"""
    mock = MagicMock()
    mock.workspace = Path("/tmp/test-workspace")
    mock.config_dir = Path("/tmp/test-config")
    mock.run_command = MagicMock(return_value="{}")
    return mock

@pytest.fixture
def test_service():
    """Sample Service instance for testing"""
    return Service(
        name="test-service",
        path=Path("/tmp/test-service"),
        config_path=Path("/tmp/test-service-config"),
        containers=[MagicMock(name="test-container")]
    )

def test_deploy_service_creates_directory_and_starts(deployment, service):
    """Verify deploy creates directory, writes compose, syncs and starts service."""
    config = {"services": {"web": {"image": "nginx"}}}
    
    # Create service directories
    service.path.mkdir(parents=True)
    service.config_path.mkdir(parents=True)
    
    deployment.deploy_service(service, config)
    
    # Verify compose file was written
    compose_file = service.config_path / "docker-compose.yml"
    assert compose_file.exists()
    assert "nginx" in compose_file.read_text()
    
    # Verify service was started
    deployment.service_manager.run_command.assert_called_with(
        f"cd {service.path} && docker-compose up -d"
    )

def test_backup_service_creates_valid_archive(deployment, service, tmp_path):
    """Test backup creates archive with config and data directories."""
    # Set up test directories and files
    service.path.mkdir(parents=True)
    service.config_path.mkdir(parents=True)
    (service.config_path / "test.conf").write_text("test config")
    
    # Mock container with test volume
    container = service.containers[0]
    container.name = "test-container"
    
    # Mock docker inspect response
    volume_dir = tmp_path / "volumes" / "test-volume"
    volume_dir.mkdir(parents=True)
    (volume_dir / "test.data").write_text("test data")
    
    deployment.service_manager.run_command.return_value = json.dumps([{
        "Mounts": [{
            "Type": "volume",
            "Name": "test-volume",
            "Source": str(volume_dir),
            "Destination": "/data"
        }]
    }])
    
    # Create backup
    backup_path = deployment.backup_service(service)
    
    # Verify backup was created
    assert backup_path.exists()
    
    # Extract and verify contents
    extract_dir = tmp_path / "extract"
    extract_dir.mkdir()
    shutil.unpack_archive(backup_path, extract_dir)
    
    assert (extract_dir / "config" / "test.conf").exists()
    assert (extract_dir / "config" / "test.conf").read_text() == "test config"
    assert (extract_dir / "data" / "test-volume" / "test.data").exists()
    assert (extract_dir / "data" / "test-volume" / "test.data").read_text() == "test data"

def test_restore_service_restores_config_and_data(deployment, service, tmp_path):
    """Test restore properly stops service, restores config and restarts."""
    # Set up test directories
    service.path.mkdir(parents=True)
    service.config_path.mkdir(parents=True)
    
    # Create test backup archive
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir(parents=True)
    config_dir = backup_dir / "config"
    data_dir = backup_dir / "data"
    config_dir.mkdir()
    data_dir.mkdir()
    
    # Add test files
    (config_dir / "test.conf").write_text("test config")
    volume_dir = data_dir / "test-volume"
    volume_dir.mkdir()
    (volume_dir / "test.data").write_text("test data")
    
    # Create archive
    archive_path = tmp_path / "test_backup.tar.gz"
    shutil.make_archive(str(archive_path.with_suffix("")), "gztar", backup_dir)
    
    # Mock volume inspect response
    volume_mount = tmp_path / "mounts" / "test-volume"
    volume_mount.mkdir(parents=True)
    deployment.service_manager.run_command.side_effect = [
        "",  # docker-compose down
        json.dumps([{"Mountpoint": str(volume_mount)}]),  # docker volume inspect
        "",  # docker-compose up
    ]
    
    # Restore from backup
    deployment.restore_service(service, archive_path)
    
    # Verify service was stopped and started
    deployment.service_manager.run_command.assert_has_calls([
        call(f"cd {service.path} && docker-compose down"),
        call("docker volume inspect test-volume"),
        call(f"cd {service.path} && docker-compose up -d")
    ])
    
    # Verify files were restored
    assert (service.config_path / "test.conf").exists()
    assert (service.config_path / "test.conf").read_text() == "test config"
    assert (volume_mount / "test.data").exists()
    assert (volume_mount / "test.data").read_text() == "test data"

def test_backup_handles_empty_volumes(deployment, service, tmp_path):
    """Test backup works when no data volumes exist."""
    # Set up test directories
    service.path.mkdir(parents=True)
    service.config_path.mkdir(parents=True)
    (service.config_path / "test.conf").write_text("test config")
    
    # Mock container with no volumes
    container = service.containers[0]
    container.name = "no-volumes"
    deployment.service_manager.run_command.return_value = json.dumps([{"Mounts": []}])
    
    # Create backup
    backup_path = deployment.backup_service(service)
    
    # Verify backup was created
    assert backup_path.exists()
    
    # Extract and verify contents
    extract_dir = tmp_path / "extract"
    extract_dir.mkdir()
    shutil.unpack_archive(backup_path, extract_dir)
    
    assert (extract_dir / "config" / "test.conf").exists()
    assert (extract_dir / "config" / "test.conf").read_text() == "test config"
    assert not (extract_dir / "data").exists() or not any((extract_dir / "data").iterdir())

def test_restore_fails_invalid_backup(deployment, service, tmp_path):
    """Test restore fails gracefully on invalid backup path."""
    # Set up test directories
    service.path.mkdir(parents=True)
    service.config_path.mkdir(parents=True)
    
    # Test with non-existent file
    with pytest.raises(FileNotFoundError):
        deployment.restore_service(service, Path("/nonexistent/backup.tar.gz"))
    
    # Test with invalid archive format
    invalid_archive = tmp_path / "invalid.tar.gz"
    invalid_archive.write_text("invalid archive content")
    
    with pytest.raises(RuntimeError) as exc_info:
        deployment.restore_service(service, invalid_archive)
    assert "Service restore failed" in str(exc_info.value)

@pytest.mark.integration
def test_real_docker_deployment(service_manager, tmp_path):
    """Integration test with real Docker setup (requires Docker env)"""
    service = Service(
        name="integration-test",
        path=tmp_path,
        config_path=tmp_path,
        containers=[MagicMock(name="integration-container")]
    )
    deployment = ServiceDeployment(service_manager)
    config = {"services": {"web": {"image": "nginx"}}}
    
    deployment.deploy_service(service, config)
    # Add Docker CLI checks here (e.g., docker ps, inspect)
