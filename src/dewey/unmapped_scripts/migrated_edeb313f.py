from pathlib import Path
from typing import Any

import pytest
import yaml
from service_manager.service_manager import ServiceManager


@pytest.fixture
def mock_service_config() -> dict[str, Any]:
    """Create mock service configuration."""
    return {
        "name": "test-service",
        "version": "1.0.0",
        "description": "Test service for unit tests",
        "maintainer": "test@example.com",
        "dependencies": ["redis", "postgres"],
        "environment": {"NODE_ENV": "production", "PORT": "3000"},
        "volumes": ["/data:/app/data", "/config:/app/config"],
        "ports": ["3000:3000", "9229:9229"],
        "healthcheck": {
            "test": ["CMD", "curl", "-f", "http://localhost:3000/health"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
        },
    }


@pytest.fixture
def mock_compose_template() -> str:
    """Create mock docker-compose template."""
    return """version: '3'
services:
  {service_name}:
    image: {image}
    container_name: {service_name}
    environment:
      {environment}
    volumes:
      {volumes}
    ports:
      {ports}
    healthcheck:
      test: {healthcheck_test}
      interval: {healthcheck_interval}
      timeout: {healthcheck_timeout}
      retries: {healthcheck_retries}
    restart: unless-stopped
"""


def test_config_validation(
    service_manager: ServiceManager,
    mock_service_config: dict[str, Any],
) -> None:
    """Test service configuration validation."""
    # Test valid config
    assert service_manager.validate_service_config(mock_service_config)

    # Test missing required fields
    invalid_config = mock_service_config.copy()
    del invalid_config["name"]
    with pytest.raises(ValueError):
        service_manager.validate_service_config(invalid_config)

    # Test invalid version format
    invalid_config = mock_service_config.copy()
    invalid_config["version"] = "1.0"
    with pytest.raises(ValueError):
        service_manager.validate_service_config(invalid_config)

    # Test invalid port format
    invalid_config = mock_service_config.copy()
    invalid_config["ports"] = ["invalid:port"]
    with pytest.raises(ValueError):
        service_manager.validate_service_config(invalid_config)


def test_config_loading(
    service_manager: ServiceManager,
    mock_service_dir: Path,
    mock_service_config: dict[str, Any],
) -> None:
    """Test service configuration loading."""
    config_file = mock_service_dir / "test-service" / "config.yml"
    config_file.parent.mkdir(parents=True, exist_ok=True)

    # Write config file
    with config_file.open("w") as f:
        yaml.dump(mock_service_config, f)

    # Test config loading
    loaded_config = service_manager.load_service_config(config_file)
    assert loaded_config == mock_service_config

    # Test config not found
    nonexistent_file = mock_service_dir / "nonexistent" / "config.yml"
    with pytest.raises(FileNotFoundError):
        service_manager.load_service_config(nonexistent_file)

    # Test invalid YAML
    with config_file.open("w") as f:
        f.write("invalid: yaml: content")
    with pytest.raises(yaml.YAMLError):
        service_manager.load_service_config(config_file)


def test_config_generation(
    service_manager: ServiceManager,
    mock_service_dir: Path,
    mock_service_config: dict[str, Any],
) -> None:
    """Test service configuration generation."""
    service_dir = mock_service_dir / "test-service"
    service_dir.mkdir(parents=True, exist_ok=True)

    # Test config generation
    config_file = service_manager.generate_service_config(
        service_dir=service_dir,
        name="test-service",
        version="1.0.0",
        description="Test service",
    )

    assert config_file.exists()
    with config_file.open() as f:
        generated_config = yaml.safe_load(f)
        assert generated_config["name"] == "test-service"
        assert generated_config["version"] == "1.0.0"
        assert generated_config["description"] == "Test service"


def test_compose_generation(
    service_manager: ServiceManager,
    mock_service_dir: Path,
    mock_service_config: dict[str, Any],
    mock_compose_template: str,
) -> None:
    """Test docker-compose.yml generation."""
    service_dir = mock_service_dir / "test-service"
    service_dir.mkdir(parents=True, exist_ok=True)

    # Write template
    template_file = service_dir / "docker-compose.template.yml"
    with template_file.open("w") as f:
        f.write(mock_compose_template)

    # Test compose file generation
    compose_file = service_manager.generate_docker_compose(
        service_dir=service_dir,
        config=mock_service_config,
        template=template_file,
    )

    assert compose_file.exists()
    with compose_file.open() as f:
        compose_data = yaml.safe_load(f)
        assert "test-service" in compose_data["services"]
        assert (
            compose_data["services"]["test-service"]["environment"]
            == mock_service_config["environment"]
        )
        assert (
            compose_data["services"]["test-service"]["ports"]
            == mock_service_config["ports"]
        )


def test_config_update(
    service_manager: ServiceManager,
    mock_service_dir: Path,
    mock_service_config: dict[str, Any],
) -> None:
    """Test service configuration updates."""
    config_file = mock_service_dir / "test-service" / "config.yml"
    config_file.parent.mkdir(parents=True, exist_ok=True)

    # Write initial config
    with config_file.open("w") as f:
        yaml.dump(mock_service_config, f)

    # Test config update
    updates = {
        "version": "1.1.0",
        "environment": {"NODE_ENV": "development", "DEBUG": "true"},
    }

    updated_config = service_manager.update_service_config(config_file, updates)
    assert updated_config["version"] == "1.1.0"
    assert updated_config["environment"]["DEBUG"] == "true"
    assert updated_config["name"] == mock_service_config["name"]


def test_config_inheritance(
    service_manager: ServiceManager,
    mock_service_dir: Path,
    mock_service_config: dict[str, Any],
) -> None:
    """Test service configuration inheritance."""
    base_config = {
        "name": "base-service",
        "version": "1.0.0",
        "environment": {"NODE_ENV": "production"},
        "volumes": ["/data:/app/data"],
    }

    # Write base config
    base_file = mock_service_dir / "base-service" / "config.yml"
    base_file.parent.mkdir(parents=True, exist_ok=True)
    with base_file.open("w") as f:
        yaml.dump(base_config, f)

    # Test config inheritance
    inherited_config = service_manager.inherit_service_config(
        base_config=base_file,
        overrides={"name": "derived-service", "environment": {"PORT": "4000"}},
    )

    assert inherited_config["name"] == "derived-service"
    assert inherited_config["version"] == base_config["version"]
    assert (
        inherited_config["environment"]["NODE_ENV"]
        == base_config["environment"]["NODE_ENV"]
    )
    assert inherited_config["environment"]["PORT"] == "4000"
    assert inherited_config["volumes"] == base_config["volumes"]


def test_config_validation_rules(
    service_manager: ServiceManager,
    mock_service_config: dict[str, Any],
) -> None:
    """Test service configuration validation rules."""
    # Test environment variable validation
    config = mock_service_config.copy()
    config["environment"]["INVALID NAME"] = "value"
    with pytest.raises(ValueError):
        service_manager.validate_environment_vars(config["environment"])

    # Test volume mount validation
    config = mock_service_config.copy()
    config["volumes"].append("invalid:mount:format")
    with pytest.raises(ValueError):
        service_manager.validate_volume_mounts(config["volumes"])

    # Test port mapping validation
    config = mock_service_config.copy()
    config["ports"].append("invalid:port:mapping")
    with pytest.raises(ValueError):
        service_manager.validate_port_mappings(config["ports"])

    # Test healthcheck validation
    config = mock_service_config.copy()
    del config["healthcheck"]["test"]
    with pytest.raises(ValueError):
        service_manager.validate_healthcheck(config["healthcheck"])


def test_config_templating(
    service_manager: ServiceManager,
    mock_service_dir: Path,
    mock_service_config: dict[str, Any],
) -> None:
    """Test service configuration templating."""
    template_vars = {
        "SERVICE_NAME": "test-service",
        "SERVICE_PORT": "3000",
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
    }

    # Create template with variables
    template_content = """
name: ${SERVICE_NAME}
version: 1.0.0
ports:
  - ${SERVICE_PORT}:${SERVICE_PORT}
environment:
  DB_URL: postgresql://${DB_HOST}:${DB_PORT}/db
"""

    template_file = mock_service_dir / "service.template.yml"
    template_file.write_text(template_content)

    # Test template rendering
    config_file = service_manager.render_config_template(
        template_file,
        template_vars,
        output_file=mock_service_dir / "config.yml",
    )

    assert config_file.exists()
    with config_file.open() as f:
        rendered_config = yaml.safe_load(f)
        assert rendered_config["name"] == template_vars["SERVICE_NAME"]
        assert (
            f"{template_vars['SERVICE_PORT']}:{template_vars['SERVICE_PORT']}"
            in rendered_config["ports"]
        )
        assert (
            f"postgresql://{template_vars['DB_HOST']}:{template_vars['DB_PORT']}/db"
            == rendered_config["environment"]["DB_URL"]
        )
