import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from service_manager.service_manager import Container, Service, ServiceManager


@pytest.fixture
def mock_container_stats() -> dict[str, Any]:
    """Create mock container statistics."""
    return {
        "test-service_web_1": {
            "cpu_percent": "2.5%",
            "memory_usage": "128MB",
            "memory_percent": "12.5%",
            "network_rx": "1.2MB",
            "network_tx": "0.8MB",
            "status": "running",
            "health": "healthy",
        },
        "test-service_db_1": {
            "cpu_percent": "5.0%",
            "memory_usage": "256MB",
            "memory_percent": "25.0%",
            "network_rx": "0.5MB",
            "network_tx": "0.3MB",
            "status": "running",
            "health": "healthy",
        },
    }


@pytest.fixture
def mock_service_logs() -> dict[str, list[str]]:
    """Create mock service logs."""
    return {
        "test-service_web_1": [
            "2024-01-01 12:00:00 [INFO] Started web server",
            "2024-01-01 12:00:05 [INFO] Accepted connection from 127.0.0.1",
        ],
        "test-service_db_1": [
            "2024-01-01 12:00:00 [INFO] Database initialized",
            "2024-01-01 12:00:10 [WARN] High memory usage detected",
        ],
    }


def test_health_check(
    service_manager: ServiceManager,
    mock_service_dir: Path,
    mock_container_stats: dict[str, Any],
) -> None:
    """Test service health check functionality."""
    service_dir = mock_service_dir / "test-service"
    service = Service(
        name="test-service",
        path=service_dir,
        containers=[
            Container(name="test-service_web_1", status="running", health="healthy"),
            Container(name="test-service_db_1", status="running", health="healthy"),
        ],
        config_path=service_manager.local_config_dir / "test-service",
    )

    # Mock container stats command
    def mock_run_remote(cmd: str) -> str:
        if "docker stats" in cmd:
            return json.dumps(mock_container_stats)
        return ""

    service_manager.run_remote_command = mock_run_remote  # type: ignore

    # Test health check
    health_status = service_manager.check_service_health(service)
    assert health_status["overall_status"] == "healthy"
    assert len(health_status["container_stats"]) == 2
    assert all(stat["status"] == "running" for stat in health_status["container_stats"])


def test_motd_update(
    service_manager: ServiceManager,
    mock_service_dir: Path,
    mock_container_stats: dict[str, Any],
) -> None:
    """Test MOTD update functionality."""
    motd_file = mock_service_dir / "motd"
    service = Service(
        name="test-service",
        path=mock_service_dir / "test-service",
        containers=[],
        config_path=service_manager.local_config_dir / "test-service",
    )

    # Mock system stats
    def mock_run_remote(cmd: str) -> str:
        if "docker stats" in cmd:
            return json.dumps(mock_container_stats)
        if "uptime" in cmd:
            return "up 7 days"
        if "df" in cmd:
            return "/ 80% used"
        return ""

    service_manager.run_remote_command = mock_run_remote  # type: ignore

    # Test MOTD update
    service_manager.update_motd([service], motd_file)
    assert motd_file.exists()

    content = motd_file.read_text()
    assert "System Status" in content
    assert "Service Status" in content
    assert "test-service" in content


def test_report_generation(
    service_manager: ServiceManager,
    mock_service_dir: Path,
    mock_container_stats: dict[str, Any],
    mock_service_logs: dict[str, list[str]],
) -> None:
    """Test report generation functionality."""
    reports_dir = mock_service_dir / "reports"
    reports_dir.mkdir(exist_ok=True)

    service = Service(
        name="test-service",
        path=mock_service_dir / "test-service",
        containers=[],
        config_path=service_manager.local_config_dir / "test-service",
    )

    # Mock monitoring data
    def mock_run_remote(cmd: str) -> str:
        if "docker stats" in cmd:
            return json.dumps(mock_container_stats)
        if "docker logs" in cmd:
            container_name = cmd.split()[-1]
            return "\n".join(mock_service_logs.get(container_name, []))
        return ""

    service_manager.run_remote_command = mock_run_remote  # type: ignore

    # Test report generation
    report = service_manager.generate_service_report(
        service,
        start_time=datetime.now() - timedelta(hours=1),
        end_time=datetime.now(),
    )

    assert isinstance(report, dict)
    assert "service_name" in report
    assert "containers" in report
    assert "logs" in report
    assert "stats" in report

    # Test report export
    report_file = reports_dir / f"{service.name}_report.json"
    service_manager.export_report(report, report_file)
    assert report_file.exists()

    with report_file.open() as f:
        saved_report = json.load(f)
        assert saved_report == report


def test_alert_monitoring(
    service_manager: ServiceManager,
    mock_service_dir: Path,
    mock_container_stats: dict[str, Any],
) -> None:
    """Test alert monitoring functionality."""
    service = Service(
        name="test-service",
        path=mock_service_dir / "test-service",
        containers=[],
        config_path=service_manager.local_config_dir / "test-service",
    )

    # Create alert rules
    alert_rules = {
        "cpu_threshold": 90.0,
        "memory_threshold": 80.0,
        "container_status": ["running"],
        "health_status": ["healthy"],
    }

    # Test with normal stats (no alerts)
    alerts = service_manager.check_alerts(service, mock_container_stats, alert_rules)
    assert len(alerts) == 0

    # Test with high CPU usage
    high_cpu_stats = mock_container_stats.copy()
    high_cpu_stats["test-service_web_1"]["cpu_percent"] = "95.0%"
    alerts = service_manager.check_alerts(service, high_cpu_stats, alert_rules)
    assert len(alerts) == 1
    assert "CPU" in alerts[0]["message"]

    # Test with unhealthy container
    unhealthy_stats = mock_container_stats.copy()
    unhealthy_stats["test-service_db_1"]["health"] = "unhealthy"
    alerts = service_manager.check_alerts(service, unhealthy_stats, alert_rules)
    assert len(alerts) == 1
    assert "health" in alerts[0]["message"]


def test_metric_collection(
    service_manager: ServiceManager,
    mock_service_dir: Path,
    mock_container_stats: dict[str, Any],
) -> None:
    """Test metric collection functionality."""
    metrics_dir = mock_service_dir / "metrics"
    metrics_dir.mkdir(exist_ok=True)

    service = Service(
        name="test-service",
        path=mock_service_dir / "test-service",
        containers=[],
        config_path=service_manager.local_config_dir / "test-service",
    )

    # Mock metric collection
    def mock_run_remote(cmd: str) -> str:
        if "docker stats" in cmd:
            return json.dumps(mock_container_stats)
        return ""

    service_manager.run_remote_command = mock_run_remote  # type: ignore

    # Test metric collection
    metrics = service_manager.collect_metrics(service)
    assert isinstance(metrics, dict)
    assert "timestamp" in metrics
    assert "containers" in metrics

    # Test metric storage
    metric_file = metrics_dir / f"{service.name}_metrics.json"
    service_manager.store_metrics(metrics, metric_file)
    assert metric_file.exists()

    with metric_file.open() as f:
        stored_metrics = json.load(f)
        assert stored_metrics == metrics
