import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from service_manager.service_manager import Service, ServiceManager


@pytest.fixture
def mock_docker_compose() -> dict[str, Any]:
    """Create a mock docker-compose configuration."""
    return {
        "version": "3",
        "services": {
            "web": {"image": "nginx:alpine", "ports": ["8080:80"]},
            "db": {
                "image": "postgres:13",
                "environment": {"POSTGRES_PASSWORD": "test"},
            },
        },
    }


@pytest.fixture
def mock_cloudflare_config() -> dict[str, Any]:
    """Create a mock Cloudflare tunnel configuration."""
    return {
        "tunnel": "test-tunnel",
        "credentials-file": "/etc/cloudflared/creds.json",
        "ingress": [
            {"hostname": "test.example.com", "service": "http://localhost:8080"},
            {"service": "http_status:404"},
        ],
    }


def test_service_deployment(
    service_manager: ServiceManager,
    mock_service_dir: Path,
    mock_docker_compose: dict[str, Any],
) -> None:
    """Test service deployment functionality."""
    service_dir = mock_service_dir / "test-service"
    compose_file = service_dir / "docker-compose.yml"

    # Write mock docker-compose.yml
    with compose_file.open("w") as f:
        yaml.dump(mock_docker_compose, f)

    # Mock deployment commands
    def mock_run_remote(cmd: str) -> str:
        if "docker-compose" in cmd and "up" in cmd:
            return "Creating test-service_web_1...\nCreating test-service_db_1..."
        return ""

    service_manager.run_remote_command = mock_run_remote  # type: ignore

    # Test deployment
    service = Service(
        name="test-service",
        path=service_dir,
        containers=[],
        config_path=service_manager.local_config_dir / "test-service",
    )

    assert service_manager.deploy_service(service)
    assert service_dir.exists()
    assert compose_file.exists()


def test_cloudflare_tunnel_config(
    service_manager: ServiceManager,
    mock_service_dir: Path,
    mock_cloudflare_config: dict[str, Any],
) -> None:
    """Test Cloudflare tunnel configuration."""
    service_dir = mock_service_dir / "test-service"
    config_dir = service_dir / "config"
    config_dir.mkdir(exist_ok=True)

    # Mock tunnel creation
    def mock_run_remote(cmd: str) -> str:
        if "cloudflared tunnel create" in cmd:
            return json.dumps({"id": "test-tunnel-id", "name": "test-tunnel"})
        if "cloudflared tunnel route dns" in cmd:
            return "Added DNS record test.example.com"
        return ""

    service_manager.run_remote_command = mock_run_remote  # type: ignore

    # Test tunnel configuration
    service = Service(
        name="test-service",
        path=service_dir,
        containers=[],
        config_path=service_manager.local_config_dir / "test-service",
    )

    assert service_manager.configure_cloudflare_tunnel(
        service=service,
        domain="example.com",
        tunnel_token="test-token",
    )

    # Verify config file was created
    config_file = config_dir / "cloudflare.yml"
    assert config_file.exists()

    # Verify config content
    with config_file.open() as f:
        config = yaml.safe_load(f)
        assert config["tunnel"] == "test-token"
        assert "test.example.com" in str(config["ingress"])


def test_service_validation(
    service_manager: ServiceManager,
    mock_service_dir: Path,
    mock_docker_compose: dict[str, Any],
) -> None:
    """Test service configuration validation."""
    service_dir = mock_service_dir / "test-service"
    compose_file = service_dir / "docker-compose.yml"

    # Write mock docker-compose.yml
    with compose_file.open("w") as f:
        yaml.dump(mock_docker_compose, f)

    service = Service(
        name="test-service",
        path=service_dir,
        containers=[],
        config_path=service_manager.local_config_dir / "test-service",
    )

    # Test valid configuration
    assert service_manager.validate_service_config(service)

    # Test invalid configuration
    invalid_compose = mock_docker_compose.copy()
    del invalid_compose["services"]
    with compose_file.open("w") as f:
        yaml.dump(invalid_compose, f)

    with pytest.raises(ValueError):
        service_manager.validate_service_config(service)


def test_service_updates(
    service_manager: ServiceManager,
    mock_service_dir: Path,
    mock_docker_compose: dict[str, Any],
) -> None:
    """Test service update functionality."""
    service_dir = mock_service_dir / "test-service"
    compose_file = service_dir / "docker-compose.yml"

    # Write initial docker-compose.yml
    with compose_file.open("w") as f:
        yaml.dump(mock_docker_compose, f)

    service = Service(
        name="test-service",
        path=service_dir,
        containers=[],
        config_path=service_manager.local_config_dir / "test-service",
    )

    # Mock update commands
    def mock_run_remote(cmd: str) -> str:
        if "docker-compose pull" in cmd:
            return "Pulling web... done\nPulling db... done"
        if "docker-compose up" in cmd:
            return "Recreating test-service_web_1...\nRecreating test-service_db_1..."
        return ""

    service_manager.run_remote_command = mock_run_remote  # type: ignore

    # Test update
    assert service_manager.update_service(service)

    # Test rollback
    assert service_manager.rollback_service(service)


def test_backup_restore(
    service_manager: ServiceManager,
    mock_service_dir: Path,
    mock_docker_compose: dict[str, Any],
) -> None:
    """Test backup and restore functionality."""
    service_dir = mock_service_dir / "test-service"
    backup_dir = mock_service_dir / "backups"
    backup_dir.mkdir(exist_ok=True)

    service = Service(
        name="test-service",
        path=service_dir,
        containers=[],
        config_path=service_manager.local_config_dir / "test-service",
    )

    # Mock backup/restore commands
    def mock_run_remote(cmd: str) -> str:
        if "tar czf" in cmd:
            return "Creating backup..."
        if "tar xzf" in cmd:
            return "Restoring from backup..."
        return ""

    service_manager.run_remote_command = mock_run_remote  # type: ignore

    # Test backup creation
    backup_file = service_manager.create_backup(service)
    assert backup_file.exists()

    # Test backup restoration
    assert service_manager.restore_backup(service, backup_file)

    # Test backup cleanup
    old_backups = service_manager.cleanup_old_backups(service, keep_days=7)
    assert isinstance(old_backups, list)
