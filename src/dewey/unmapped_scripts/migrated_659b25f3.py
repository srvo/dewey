from __future__ import annotations

import json
import shutil
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from pathlib import Path


def _has_config(service_dir: Path) -> bool:
    """Check if directory contains service configuration.

    Args:
    ----
        service_dir: Service directory to check

    Returns:
    -------
        True if directory contains configuration

    """
    return (service_dir / "docker-compose.yml").exists() or (
        service_dir / "service.json"
    ).exists()


def _load_config(config_path: Path) -> dict[str, Any]:
    """Load configuration from a file (YAML or JSON).

    Args:
    ----
        config_path: Path to the configuration file.

    Returns:
    -------
        The loaded configuration as a dictionary.

    """
    with open(config_path) as f:
        if config_path.suffix in (".yml", ".yaml"):
            return yaml.safe_load(f)
        return json.load(f)


class ServiceConfig:
    """Service configuration management."""

    def __init__(self, config_dir: Path) -> None:
        """Initialize ServiceConfig.

        Args:
        ----
            config_dir: Directory containing service configurations.

        """
        self.config_dir: Path = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load_service_config(self, service_name: str) -> dict[str, Any]:
        """Load service configuration.

        Args:
        ----
            service_name: Name of service.

        Returns:
        -------
            Service configuration dictionary.

        Raises:
        ------
            FileNotFoundError: If service configuration does not exist.

        """
        # Check for docker-compose.yml first
        compose_path: Path = self.config_dir / service_name / "docker-compose.yml"
        if compose_path.exists():
            return _load_config(compose_path)

        # Check for service.json
        json_path: Path = self.config_dir / service_name / "service.json"
        if json_path.exists():
            return _load_config(json_path)

        msg = f"No configuration found for service: {service_name}"
        raise FileNotFoundError(msg)

    def save_service_config(
        self,
        service_name: str,
        config: dict[str, Any],
        format: str = "yaml",
    ) -> None:
        """Save service configuration.

        Args:
        ----
            service_name: Name of service.
            config: Service configuration.
            format: Configuration format ("yaml" or "json").

        """
        service_dir: Path = self.config_dir / service_name
        service_dir.mkdir(parents=True, exist_ok=True)

        if format == "yaml":
            path: Path = service_dir / "docker-compose.yml"
            with open(path, "w") as f:
                yaml.safe_dump(config, f, default_flow_style=False)
        else:
            path: Path = service_dir / "service.json"
            with open(path, "w") as f:
                json.dump(config, f, indent=2)

    def list_services(self) -> list[str]:
        """List available services.

        Returns
        -------
            List of service names.

        """
        return [
            d.name for d in self.config_dir.iterdir() if d.is_dir() and _has_config(d)
        ]

    def get_service_template(self, template_name: str) -> dict[str, Any]:
        """Get service configuration template.

        Args:
        ----
            template_name: Name of template.

        Returns:
        -------
            Template configuration dictionary.

        Raises:
        ------
            FileNotFoundError: If template does not exist.

        """
        template_dir: Path = self.config_dir / "templates"
        template_path: Path = template_dir / f"{template_name}.yml"

        if not template_path.exists():
            template_path = template_dir / f"{template_name}.json"

        if not template_path.exists():
            msg = f"Template not found: {template_name}"
            raise FileNotFoundError(msg)

        return _load_config(template_path)

    def create_service_config(
        self,
        service_name: str,
        template_name: str,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create service configuration from template.

        Args:
        ----
            service_name: Name of service.
            template_name: Name of template.
            variables: Template variables.

        Returns:
        -------
            Generated service configuration.

        """
        from .utils import template_config, validate_config

        template: dict[str, Any] = self.get_service_template(template_name)

        config: dict[str, Any]
        if variables:
            config = template_config(template, **variables)
        else:
            config = template.copy()

        # Add service name if not present
        if "name" not in config:
            config["name"] = service_name

        # Validate configuration
        validate_config(config)

        # Save configuration
        self.save_service_config(service_name, config)

        return config

    def update_service_config(
        self,
        service_name: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Update service configuration.

        Args:
        ----
            service_name: Name of service.
            updates: Configuration updates.

        Returns:
        -------
            Updated service configuration.

        """
        from .utils import merge_configs, validate_config

        current: dict[str, Any] = self.load_service_config(service_name)
        updated: dict[str, Any] = merge_configs(current, updates)

        # Validate configuration
        validate_config(updated)

        # Save configuration
        self.save_service_config(service_name, updated)

        return updated

    def delete_service_config(self, service_name: str) -> None:
        """Delete service configuration.

        Args:
        ----
            service_name: Name of service.

        """
        service_dir: Path = self.config_dir / service_name
        if service_dir.exists():
            shutil.rmtree(service_dir)
