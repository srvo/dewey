import json
import subprocess
from pathlib import Path

import pytest
from service_manager.service_manager import Service, ServiceManager


def test_service_discovery(
    service_manager: ServiceManager,
    mock_service_dir: Path,
) -> None:
    """Test that services are correctly discovered."""

    # Mock the remote command to list services
    def mock_run_remote(cmd: str) -> str:
        if cmd == "ls -1 /opt":
            return "test-service\ndifyv2\ngitea\n"
        return ""

    service_manager.run_remote_command = mock_run_remote  # type: ignore

    services = service_manager.get_services()
    assert len(services) == 3
    assert services[0].name == "test-service"
    assert services[1].name == "difyv2"
    assert services[2].name == "gitea"


def test_container_matching(service_manager: ServiceManager) -> None:
    """Test that containers are correctly matched to services."""
    # Mock container data
    mock_ps_output = [
        json.dumps({"Names": "test-service-1", "Image": "nginx:alpine"}),
        json.dumps({"Names": "test-service-db", "Image": "postgres:13"}),
    ]

    mock_inspect_output = json.dumps(
        [
            {
                "State": {
                    "Status": "running",
                    "StartedAt": "2024-03-12T00:00:00Z",
                    "Health": {"Status": "healthy"},
                },
            },
        ],
    )

    def mock_run_remote(cmd: str) -> str:
        if "docker ps" in cmd:
            return "\n".join(mock_ps_output)
        if "docker inspect" in cmd:
            return mock_inspect_output
        return ""

    service_manager.run_remote_command = mock_run_remote  # type: ignore

    containers = service_manager.find_matching_containers("test-service")
    assert len(containers) == 2
    assert containers[0].name == "test-service-1"
    assert containers[0].status == "running"
    assert containers[0].health == "healthy"


def test_config_sync(service_manager: ServiceManager, mock_service_dir: Path) -> None:
    """Test configuration synchronization."""
    service = Service(
        name="test-service",
        path=mock_service_dir / "test-service",
        containers=[],
        config_path=service_manager.local_config_dir / "test-service",
    )

    # Test initial sync
    service_manager.sync_service_config(service)
    assert service.config_path.exists()
    assert (service.config_path / "docker-compose.yml").exists()

    # Test re-sync with no changes
    service_manager.sync_service_config(service)
    # Should not raise any errors


def test_service_analysis(
    service_manager: ServiceManager,
    mock_service_dir: Path,
) -> None:
    """Test complete service analysis."""
    # Mock container data
    mock_ps_output = json.dumps({"Names": "test-service-1", "Image": "nginx:alpine"})
    mock_inspect_output = json.dumps(
        [
            {
                "State": {
                    "Status": "running",
                    "StartedAt": "2024-03-12T00:00:00Z",
                    "Health": {"Status": "healthy"},
                },
            },
        ],
    )
    mock_stats_output = json.dumps({"CPUPerc": "0.00%", "MemUsage": "1.5MiB / 2GiB"})
    mock_logs = "Test log line 1\nTest log line 2"

    def mock_run_remote(cmd: str) -> str:
        if "ls -1 /opt" in cmd:
            return "test-service"
        if "docker ps" in cmd:
            return mock_ps_output
        if "docker inspect" in cmd:
            return mock_inspect_output
        if "docker stats" in cmd:
            return mock_stats_output
        if "docker logs" in cmd:
            return mock_logs
        return ""

    service_manager.run_remote_command = mock_run_remote  # type: ignore

    # Capture output and check for expected content
    service_manager.analyze_services()
    # Should not raise any errors


def test_get_services_error(service_manager) -> None:
    """Test error handling in get_services."""

    def mock_run_remote_error(cmd: str) -> str:
        raise subprocess.CalledProcessError(1, cmd, "Mock error")

    service_manager.run_remote_command = mock_run_remote_error  # type: ignore

    with pytest.raises(subprocess.CalledProcessError):
        service_manager.get_services()


@pytest.mark.parametrize(
    ("service_name", "expected_matches"),
    [
        ("test_service", ["test-service-1", "test-service-db"]),
        ("dify", ["difyv2-api", "difyv2-web"]),
        ("nonexistent", []),
    ],
)
def test_container_name_matching(
    service_manager: ServiceManager,
    service_name: str,
    expected_matches: list[str],
) -> None:
    """Test container name matching with various patterns."""
    mock_containers = {
        "test-service-1": "nginx:alpine",
        "test-service-db": "postgres:13",
        "difyv2-api": "dify:latest",
        "difyv2-web": "nginx:alpine",
    }

    def mock_run_remote(cmd: str) -> str:
        if "docker ps" in cmd:
            return "\n".join(
                json.dumps({"Names": name, "Image": image})
                for name, image in mock_containers.items()
            )
        if "docker inspect" in cmd:
            return json.dumps(
                [{"State": {"Status": "running", "StartedAt": "2024-03-12T00:00:00Z"}}],
            )
        return ""

    service_manager.run_remote_command = mock_run_remote  # type: ignore

    containers = service_manager.find_matching_containers(service_name)
    container_names = [c.name for c in containers]
    assert container_names == expected_matches
