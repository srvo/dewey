import pytest
from unittest.mock import MagicMock, patch, call
from pathlib import Path
from src.dewey.core.automation.service_deployment import ServiceDeployment, Service
from typing import Any
import shutil
import tempfile
from datetime import datetime

@pytest.fixture
def mock_service_manager():
    """Fixture for mocked ServiceManager instance."""
    mock = MagicMock()
    mock.workspace = Path("/workspace")
    mock.config_dir = Path("/config")
    return mock

@pytest.fixture
def service():
    """Fixture for mocked Service instance."""
    service = MagicMock(spec=Service)
    service.name = "test-service"
    service.path = Path("/service/path")
    service.config_path = Path("/config/path")
    service.containers = [MagicMock(name="container1")]
    return service

@pytest.fixture
def temp_dir(tmp_path):
    """Fixture for temporary directory."""
    return tmp_path

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
def test_create_archive(mock_datetime, timestamp, mock_service_manager, service):
    """Test archive naming and creation."""
    mock_datetime.now.return_value.strftime.return_value = timestamp
    deployment = ServiceDeployment(mock_service_manager)
    with tempfile.TemporaryDirectory() as temp_dir:
        backup_dir = Path(temp_dir)
        archive_path = deployment._create_archive(service, backup_dir)

        assert archive_path == Path("/workspace/backups/test-service_backup_20250317_120000.tar.gz")
        assert archive_path.parent.exists()
        shutil.unpack_archive(archive_path, extract_dir=temp_dir)
        assert (Path(temp_dir) / "config").exists()

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

def test_deploy_service_creates_directory_and_starts(service_manager, test_service):
    """Verify deploy creates directory, writes compose, syncs and starts service"""
    deployment = ServiceDeployment(service_manager)
    config = {"services": {"web": {"image": "nginx"}}}
    
    deployment.deploy_service(test_service, config)
    
    service_manager.run_command.assert_any_call(f"mkdir -p {test_service.path}")
    service_manager.run_command.assert_any_call(f"cd {test_service.path} && docker-compose up -d")
    
    compose_path = test_service.config_path / "docker-compose.yml"
    assert compose_path.exists()
    assert "nginx" in compose_path.read_text()

def test_backup_service_creates_valid_archive(service_manager, test_service, tmp_path):
    """Test backup creates archive with config and data directories"""
    deployment = ServiceDeployment(service_manager)
    test_config_path = tmp_path / "config"
    test_config_path.mkdir()
    (test_config_path / "test.conf").touch()
    test_service.config_path = test_config_path
    
    backup_path = deployment.backup_service(test_service)
    assert backup_path.exists()
    
    # Verify archive contents
    with tempfile.TemporaryDirectory() as extract_dir:
        shutil.unpack_archive(backup_path, extract_dir)
        extracted_config = Path(extract_dir) / "config"
        assert (extracted_config / "test.conf").exists()

def test_restore_service_restores_config_and_data(service_manager, test_service, tmp_path):
    """Test restore properly stops service, restores config and restarts"""
    deployment = ServiceDeployment(service_manager)
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()
    (backup_dir / "config").mkdir()
    (backup_dir / "data").mkdir()
    
    deployment.restore_service(test_service, backup_dir)
    
    service_manager.run_command.assert_any_call(f"docker volume rm -f test-container")
    assert (test_service.config_path / "config").exists()
    service_manager.run_command.assert_any_call(f"cd {test_service.path} && docker-compose up -d")

def test_backup_handles_empty_volumes(service_manager, test_service):
    """Test backup works when no data volumes exist"""
    test_service.containers[0].name = "no-volumes"
    service_manager.run_command.side_effect = ["[]", ""]
    
    deployment = ServiceDeployment(service_manager)
    backup_path = deployment.backup_service(test_service)
    assert backup_path.exists()

def test_restore_fails_invalid_backup(service_manager, test_service):
    """Test restore fails gracefully on invalid backup path"""
    with pytest.raises(FileNotFoundError):
        deployment = ServiceDeployment(service_manager)
        deployment.restore_service(test_service, Path("/invalid"))

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
