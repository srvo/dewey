from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, NoReturn

import pytest
import yaml
from service_manager.service_manager import ServiceManager


@pytest.fixture
def mock_config() -> dict[str, Any]:
    """Create mock configuration data."""
    return {
        "services_dir": "/opt/services",
        "config_dir": "/etc/service-manager",
        "backup_dir": "/var/backups/services",
        "log_dir": "/var/log/service-manager",
        "github": {"owner": "test-owner", "repo": "test-repo", "token": "test-token"},
        "monitoring": {
            "check_interval": 300,
            "alert_thresholds": {"cpu": 90, "memory": 80, "disk": 85},
        },
    }


def test_config_loading(
    service_manager: ServiceManager,
    mock_service_dir: Path,
    mock_config: dict[str, Any],
) -> None:
    """Test configuration loading functionality."""
    config_file = mock_service_dir / "config.yml"

    # Write mock config
    with config_file.open("w") as f:
        yaml.dump(mock_config, f)

    # Test config loading
    loaded_config = service_manager.load_config(config_file)
    assert loaded_config == mock_config

    # Test config validation
    assert service_manager.validate_config(loaded_config)

    # Test invalid config
    invalid_config = mock_config.copy()
    del invalid_config["services_dir"]
    with pytest.raises(ValueError):
        service_manager.validate_config(invalid_config)


def test_path_handling(service_manager: ServiceManager, mock_service_dir: Path) -> None:
    """Test path handling functionality."""
    # Test path normalization
    path = service_manager.normalize_path("~/services/test")
    assert isinstance(path, Path)
    assert not path.is_absolute() or str(path).startswith("/")

    # Test path validation
    assert service_manager.is_safe_path(mock_service_dir / "test")
    assert not service_manager.is_safe_path("/root/test")

    # Test path creation
    new_dir = mock_service_dir / "new_service"
    service_manager.ensure_directory(new_dir)
    assert new_dir.exists()
    assert new_dir.is_dir()


def test_logging(service_manager: ServiceManager, mock_service_dir: Path) -> None:
    """Test logging functionality."""
    log_file = mock_service_dir / "service_manager.log"

    # Test log message
    service_manager.log_message("Test message", level="INFO", log_file=log_file)
    assert log_file.exists()

    content = log_file.read_text()
    assert "Test message" in content
    assert "INFO" in content
    assert datetime.now().strftime("%Y-%m-%d") in content

    # Test log rotation
    old_log = mock_service_dir / "service_manager.log.1"
    service_manager.rotate_logs(log_file, max_size=1024, keep_count=3)
    if old_log.exists():
        assert old_log.stat().st_size <= 1024


def test_command_execution(service_manager: ServiceManager) -> None:
    """Test command execution functionality."""
    # Test command validation
    assert service_manager.is_safe_command("docker ps")
    assert not service_manager.is_safe_command("rm -rf /")

    # Test command execution
    result = service_manager.run_command("echo 'test'")
    assert result.strip() == "test"

    # Test command failure handling
    with pytest.raises(RuntimeError):
        service_manager.run_command("nonexistent-command")


def test_string_formatting(service_manager: ServiceManager) -> None:
    """Test string formatting functionality."""
    # Test string sanitization
    assert service_manager.sanitize_string("test-service!@#") == "test-service"

    # Test string truncation
    assert len(service_manager.truncate_string("x" * 100, max_length=50)) <= 50

    # Test string template rendering
    template = "Service {name} is {status}"
    context = {"name": "test", "status": "running"}
    rendered = service_manager.render_template(template, context)
    assert rendered == "Service test is running"


def test_time_handling(service_manager: ServiceManager) -> None:
    """Test time handling functionality."""
    # Test timestamp generation
    timestamp = service_manager.generate_timestamp()
    assert isinstance(timestamp, str)
    datetime.strptime(timestamp, "%Y-%m-%d_%H-%M-%S")

    # Test duration formatting
    duration = timedelta(hours=2, minutes=30)
    formatted = service_manager.format_duration(duration)
    assert "2 hours" in formatted
    assert "30 minutes" in formatted

    # Test time parsing
    parsed = service_manager.parse_time("2024-01-01 12:00:00")
    assert isinstance(parsed, datetime)
    assert parsed.year == 2024


def test_data_validation(service_manager: ServiceManager) -> None:
    """Test data validation functionality."""
    # Test service name validation
    assert service_manager.is_valid_service_name("test-service")
    assert not service_manager.is_valid_service_name("test/service")

    # Test version string validation
    assert service_manager.is_valid_version("1.0.0")
    assert not service_manager.is_valid_version("1.0")

    # Test URL validation
    assert service_manager.is_valid_url("https://example.com")
    assert not service_manager.is_valid_url("not-a-url")


def test_data_conversion(service_manager: ServiceManager) -> None:
    """Test data conversion functionality."""
    # Test size conversion
    assert service_manager.convert_size(1024) == "1.0 KB"
    assert service_manager.convert_size(1024 * 1024) == "1.0 MB"

    # Test duration conversion
    assert service_manager.convert_duration(3600) == "1 hour"
    assert service_manager.convert_duration(90) == "1 minute 30 seconds"

    # Test status conversion
    assert service_manager.convert_status("running") == "Running"
    assert service_manager.convert_status("exited") == "Stopped"


def test_cache_handling(
    service_manager: ServiceManager,
    mock_service_dir: Path,
) -> None:
    """Test cache handling functionality."""
    cache_file = mock_service_dir / "cache.json"

    # Test cache writing
    data = {"key": "value"}
    service_manager.write_cache(data, cache_file)
    assert cache_file.exists()

    # Test cache reading
    cached_data = service_manager.read_cache(cache_file)
    assert cached_data == data

    # Test cache invalidation
    service_manager.invalidate_cache(cache_file)
    assert not cache_file.exists()


def test_error_handling(service_manager: ServiceManager) -> NoReturn:
    """Test error handling functionality."""
    # Test error wrapping
    with pytest.raises(RuntimeError) as exc:
        with service_manager.error_handler("Test operation"):
            msg = "Test error"
            raise ValueError(msg)
    assert "Test operation" in str(exc.value)
    assert "Test error" in str(exc.value)

    # Test error formatting
    error = ValueError("Test error")
    formatted = service_manager.format_error(error)
    assert "ValueError" in formatted
    assert "Test error" in formatted

    # Test error categorization
    assert service_manager.categorize_error(ValueError()) == "validation_error"
    assert service_manager.categorize_error(FileNotFoundError()) == "file_error"
