```python
import os
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from unittest.mock import MagicMock

# Define custom exceptions for clarity
class InvalidConfigError(ValueError):
    """Raised when the service configuration is invalid."""
    pass

class ConfigLoadingError(IOError):
    """Raised when there's an error loading the configuration."""
    pass

class ConfigGenerationError(IOError):
    """Raised when there's an error generating the configuration."""
    pass

class ConfigUpdateError(IOError):
    """Raised when there's an error updating the configuration."""
    pass

class ConfigInheritanceError(ValueError):
    """Raised when there's an error inheriting the configuration."""
    pass

class ConfigTemplatingError(ValueError):
    """Raised when there's an error templating the configuration."""
    pass


class ServiceManager:
    """
    Manages service configurations, including validation, loading, generation,
    updating, inheritance, and templating.
    """

    def __init__(self, config_schema: Optional[Dict[str, Any]] = None):
        """
        Initializes the ServiceManager.

        Args:
            config_schema: Optional schema for validating configurations.
                           Defaults to None (no validation).
        """
        self.config_schema = config_schema

    def validate_service_config(self, config: Dict[str, Any]) -> None:
        """
        Validates the service configuration against a predefined schema.

        Args:
            config: The service configuration to validate.

        Raises:
            InvalidConfigError: If the configuration is invalid.
        """
        if self.config_schema is None:
            return  # No validation if no schema is provided

        # Example validation (replace with your actual validation logic)
        if not isinstance(config, dict):
            raise InvalidConfigError("Configuration must be a dictionary.")
        if "name" not in config or not isinstance(config["name"], str):
            raise InvalidConfigError("Configuration must have a 'name' (string).")
        if "port" in config and not isinstance(config["port"], int):
            raise InvalidConfigError("Configuration port must be an integer.")
        if "version" not in config or not isinstance(config["version"], str):
            raise InvalidConfigError("Configuration must have a 'version' (string).")

    def validate_port_mappings(self, ports: List[str]) -> None:
        """
        Validates port mappings in the service configuration.

        Args:
            ports: A list of port mappings (e.g., ["80:80", "443:443"]).

        Raises:
            ValueError: If any port mapping is invalid.
        """
        if not isinstance(ports, list):
            raise ValueError("Ports must be a list.")
        for port_mapping in ports:
            if not isinstance(port_mapping, str):
                raise ValueError("Port mappings must be strings.")
            try:
                parts = port_mapping.split(":")
                if len(parts) != 2:
                    raise ValueError
                int(parts[0])
                int(parts[1])
            except ValueError:
                raise ValueError(f"Invalid port mapping format: {port_mapping}")

    def validate_environment_vars(self, env_vars: Dict[str, str]) -> None:
        """
        Validates environment variables in the service configuration.

        Args:
            env_vars: A dictionary of environment variables (e.g., {"NODE_ENV": "production"}).

        Raises:
            ValueError: If any environment variable is invalid.
        """
        if not isinstance(env_vars, dict):
            raise ValueError("Environment variables must be a dictionary.")
        for key, value in env_vars.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValueError("Environment variable keys and values must be strings.")

    def validate_healthcheck(self, healthcheck: Dict[str, Any]) -> None:
        """
        Validates healthcheck configuration.

        Args:
            healthcheck: A dictionary containing healthcheck configuration.

        Raises:
            ValueError: If the healthcheck configuration is invalid.
        """
        if not isinstance(healthcheck, dict):
            raise ValueError("Healthcheck must be a dictionary.")
        if "test" not in healthcheck or not isinstance(healthcheck["test"], list):
            raise ValueError("Healthcheck must have a 'test' (list).")
        # Add more specific validation rules for the 'test' list as needed.

    def validate_volume_mounts(self, volumes: List[str]) -> None:
        """
        Validates volume mounts in the service configuration.

        Args:
            volumes: A list of volume mount strings (e.g., ["/data:/app/data"]).

        Raises:
            ValueError: If any volume mount is invalid.
        """
        if not isinstance(volumes, list):
            raise ValueError("Volumes must be a list.")
        for volume_mount in volumes:
            if not isinstance(volume_mount, str):
                raise ValueError("Volume mounts must be strings.")
            try:
                parts = volume_mount.split(":")
                if len(parts) != 2:
                    raise ValueError
            except ValueError:
                raise ValueError(f"Invalid volume mount format: {volume_mount}")

    def load_service_config(self, config_file: Path) -> Dict[str, Any]:
        """
        Loads a service configuration from a YAML file.

        Args:
            config_file: The path to the YAML configuration file.

        Returns:
            The service configuration as a dictionary.

        Raises:
            ConfigLoadingError: If the file is not found or cannot be parsed.
        """
        try:
            with open(config_file, "r") as f:
                config = yaml.safe_load(f)
                if config is None:
                    return {}  # Handle empty files gracefully
                return config
        except FileNotFoundError:
            raise ConfigLoadingError(f"Configuration file not found: {config_file}")
        except yaml.YAMLError as e:
            raise ConfigLoadingError(f"Error parsing YAML file: {e}")

    def generate_service_config(
        self,
        service_name: str,
        version: str = "1.0.0",
        description: str = "Default service description",
        port: Optional[int] = None,
        environment: Optional[Dict[str, str]] = None,
        volume: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generates a basic service configuration.

        Args:
            service_name: The name of the service.
            version: The service version.
            description: A description of the service.
            port: The service port.
            environment: Environment variables for the service.
            volume: Volume mounts for the service.

        Returns:
            A dictionary representing the service configuration.
        """
        config: Dict[str, Any] = {
            "name": service_name,
            "version": version,
            "description": description,
        }
        if port is not None:
            config["port"] = port
        if environment is not None:
            config["environment"] = environment
        if volume is not None:
            config["volume"] = volume
        return config

    def generate_docker_compose(
        self, service_config: Dict[str, Any], template: str
    ) -> Dict[str, Any]:
        """
        Generates a docker-compose configuration based on a service configuration and a template.

        Args:
            service_config: The service configuration.
            template: The docker-compose template string.

        Returns:
            A dictionary representing the docker-compose configuration.
        """
        try:
            compose_data = yaml.safe_load(template)
        except yaml.YAMLError as e:
            raise ConfigGenerationError(f"Error parsing docker-compose template: {e}")

        service_name = service_config.get("name", "default_service")
        compose_data["services"][service_name] = {
            "image": f"{service_name}:latest",  # Default image
            "restart": "always",
            "environment": service_config.get("environment", {}),
        }

        if "port" in service_config:
            compose_data["services"][service_name]["ports"] = [
                f"{service_config['port']}:{service_config['port']}"
            ]
        if "volume" in service_config:
            compose_data["services"][service_name]["volumes"] = service_config["volume"]

        return compose_data

    def update_service_config(
        self, config_file: Path, updates: Dict[str, Any]
    ) -> None:
        """
        Updates a service configuration file with new values.

        Args:
            config_file: The path to the configuration file.
            updates: A dictionary of updates to apply.

        Raises:
            ConfigUpdateError: If there's an error reading or writing the file.
        """
        try:
            config = self.load_service_config(config_file)
            config.update(updates)
            with open(config_file, "w") as f:
                yaml.dump(config, f, indent=2)
        except (ConfigLoadingError, IOError) as e:
            raise ConfigUpdateError(f"Error updating configuration: {e}")

    def inherit_service_config(
        self, base_config: Dict[str, Any], overrides: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Inherits a service configuration from a base configuration, applying overrides.

        Args:
            base_config: The base service configuration.
            overrides: A dictionary of overrides to apply.

        Returns:
            The inherited service configuration.
        """
        inherited_config = base_config.copy()
        inherited_config.update(overrides)
        return inherited_config

    def render_config_template(
        self,
        template_content: str,
        template_vars: Dict[str, str],
        config_file: Path,
    ) -> Dict[str, Any]:
        """
        Renders a service configuration template with provided variables.

        Args:
            template_content: The content of the template (e.g., a string with placeholders).
            template_vars: A dictionary of variables to substitute in the template.
            config_file: The path to the output config file.

        Returns:
            The rendered service configuration as a dictionary.

        Raises:
            ConfigTemplatingError: If there's an error during templating or file operations.
        """
        try:
            rendered_content = template_content.format(**template_vars)
            rendered_config = yaml.safe_load(rendered_content)

            # Write the rendered config to the file
            with open(config_file, "w") as f:
                yaml.dump(rendered_config, f, indent=2)

            return rendered_config

        except (KeyError, ValueError, yaml.YAMLError) as e:
            raise ConfigTemplatingError(f"Error rendering template: {e}")
        except IOError as e:
            raise ConfigTemplatingError(f"Error writing rendered config to file: {e}")


def mock_service_config() -> Dict[str, Any]:
    """
    Creates a mock service configuration.

    Returns:
        A dictionary representing a mock service configuration.
    """
    return {
        "name": "test-service",
        "version": "1.0.0",
        "description": "A test service",
        "port": 8080,
        "environment": {"NODE_ENV": "production", "PORT": "8080"},
        "volume": ["/data:/app/data"],
        "healthcheck": {"test": ["curl", "http://localhost:8080/health"]},
    }


def mock_compose_template() -> str:
    """
    Creates a mock docker-compose template.

    Returns:
        A string representing a mock docker-compose template.
    """
    return """
version: "3.8"
services:
  {service_name}:
    image: {service_name}:latest
    restart: always
    environment:
      - NODE_ENV=production
    ports:
      - "{port}:{port}"
    volumes:
      - /data:/app/data
"""


def test_config_validation(
    service_manager: ServiceManager, mock_service_config: Dict[str, Any]
) -> None:
    """
    Tests service configuration validation.

    Args:
        service_manager: An instance of ServiceManager.
        mock_service_config: A mock service configuration.
    """
    # Valid config
    service_manager.validate_service_config(mock_service_config.copy())

    # Invalid config (missing name)
    invalid_config = mock_service_config.copy()
    del invalid_config["name"]
    try:
        service_manager.validate_service_config(invalid_config)
        assert False, "Expected InvalidConfigError for missing name"
    except InvalidConfigError:
        pass

    # Invalid config (invalid port)
    invalid_config = mock_service_config.copy()
    invalid_config["port"] = "invalid"
    try:
        service_manager.validate_service_config(invalid_config)
        assert False, "Expected InvalidConfigError for invalid port"
    except InvalidConfigError:
        pass

    # Invalid config (missing version)
    invalid_config = mock_service_config.copy()
    del invalid_config["version"]
    try:
        service_manager.validate_service_config(invalid_config)
        assert False, "Expected InvalidConfigError for missing version"
    except InvalidConfigError:
        pass


def test_config_loading(
    service_manager: ServiceManager,
    mock_service_dir: Path,
    mock_service_config: Dict[str, Any],
) -> None:
    """
    Tests service configuration loading.

    Args:
        service_manager: An instance of ServiceManager.
        mock_service_dir: A Path object representing a mock service directory.
        mock_service_config: A mock service configuration.
    """
    config_file = mock_service_dir / "service.yaml"
    with open(config_file, "w") as f:
        yaml.dump(mock_service_config, f)

    # Load valid config
    loaded_config = service_manager.load_service_config(config_file)
    assert loaded_config == mock_service_config

    # Load from a non-existent file
    nonexistent_file = mock_service_dir / "nonexistent.yaml"
    try:
        service_manager.load_service_config(nonexistent_file)
        assert False, "Expected ConfigLoadingError for non-existent file"
    except ConfigLoadingError:
        pass

    # Load invalid YAML
    invalid_file = mock_service_dir / "invalid.yaml"
    with open(invalid_file, "w") as f:
        f.write("invalid: file")
    try:
        service_manager.load_service_config(invalid_file)
        assert False, "Expected ConfigLoadingError for invalid YAML"
    except ConfigLoadingError:
        pass


def test_config_generation(
    service_manager: ServiceManager,
    mock_service_dir: Path,
    mock_service_config: Dict[str, Any],
) -> None:
    """
    Tests service configuration generation.

    Args:
        service_manager: An instance of ServiceManager.
        mock_service_dir: A Path object representing a mock service directory.
        mock_service_config: A mock service configuration.
    """
    # Generate config
    generated_config = service_manager.generate_service_config(
        service_name=mock_service_config["name"],
        version=mock_service_config["version"],
        description=mock_service_config["description"],
        port=mock_service_config["port"],
        environment=mock_service_config["environment"],
        volume=mock_service_config["volume"],
    )
    assert generated_config["name"] == mock_service_config["name"]
    assert generated_config["version"] == mock_service_config["version"]
    assert generated_config["description"] == mock_service_config["description"]
    assert generated_config["port"] == mock_service_config["port"]
    assert generated_config["environment"] == mock_service_config["environment"]
    assert generated_config["volume"] == mock_service_config["volume"]


def test_compose_generation(
    service_manager: ServiceManager,
    mock_service_dir: Path,
    mock_service_config: Dict[str, Any],
    mock_compose_template: str,
) -> None:
    """
    Tests docker-compose.yml generation.

    Args:
        service_manager: An instance of ServiceManager.
        mock_service_dir: A Path object representing a mock service directory.
        mock_service_config: A mock service configuration.
        mock_compose_template: A mock docker-compose template.
    """
    # Generate compose file
    generated_compose = service_manager.generate_docker_compose(
        mock_service_config, mock_compose_template
    )
    assert "services" in generated_compose
    assert mock_service_config["name"] in generated_compose["services"]
    service_config = generated_compose["services"][mock_service_config["name"]]
    assert service_config["image"] == f"{mock_service_config['name']}:latest"
    assert service_config["restart"] == "always"
    assert service_config["environment"] == mock_service_config["environment"]
    assert service_config["ports"] == [
        f"{mock_service_config['port']}:{mock_service_config['port']}"
    ]
    assert service_config["volumes"] == mock_service_config["volume"]


def test_config_update(
    service_manager: ServiceManager,
    mock_service_dir: Path,
    mock_service_config: Dict[str, Any],
) -> None:
    """
    Tests service configuration updates.

    Args:
        service_manager: An instance of ServiceManager.
        mock_service_dir: A Path object representing a mock service directory.
        mock_service_config: A mock service configuration.
    """
    config_file = mock_service_dir / "service.yaml"
    with open(config_file, "w") as f:
        yaml.dump(mock_service_config, f)

    # Update config
    updates = {"version": "1.1.0", "environment": {"NODE_ENV": "development"}}
    service_manager.update_service_config(config_file, updates)
    updated_config = service_manager.load_service_config(config_file)
    assert updated_config["name"] == mock_service_config["name"]
    assert updated_config["version"] == "1.1.0"
    assert updated_config["environment"]["NODE_ENV"] == "development"


def test_config_inheritance(
    service_manager: ServiceManager,
    mock_service_dir: Path,
    mock_service_config: Dict[str, Any],
) -> None:
    """
    Tests service configuration inheritance.

    Args:
        service_manager: An instance of ServiceManager.
        mock_service_dir: A Path object representing a mock service directory.
        mock_service_config: A mock service configuration.
    """
    base_config = {
        "name": "base-service",
        "version": "1.0.0",
        "volume": ["/data:/app/data"],
    }
    overrides = {
        "name": "derived-service",
        "version": "1.1.0",
        "environment": {"NODE_ENV": "production"},
    }

    inherited_config = service_manager.inherit_service_config(base_config, overrides)
    assert inherited_config["name"] == "derived-service"
    assert inherited_config["version"] == "1.1.0"
    assert inherited_config["volume"] == ["/data:/app/data"]
    assert inherited_config["environment"]["NODE_ENV"] == "production"


def test_config_validation_rules(
    service_manager: ServiceManager, mock_service_config: Dict[str, Any]
) -> None:
    """
    Tests service configuration validation rules.

    Args:
        service_manager: An instance of ServiceManager.
        mock_service_config: A mock service configuration.
    """
    # Test port validation
    config = mock_service_config.copy()
    config["ports"] = ["invalid"]
    try:
        service_manager.validate_port_mappings(config["ports"])
        assert False, "Expected ValueError for invalid port mapping"
    except ValueError:
        pass

    # Test environment variable validation
    config = mock_service_config.copy()
    config["environment"] = {"INVALID": 123}
    try:
        service_manager.validate_environment_vars(config["environment"])
        assert False, "Expected ValueError for invalid environment variable"
    except ValueError:
        pass

    # Test healthcheck validation
    config = mock_service_config.copy()
    config["healthcheck"] = {"test": ["invalid"]}
    try:
        service_manager.validate_healthcheck(config["healthcheck"])
        assert False, "Expected ValueError for invalid healthcheck"
    except ValueError:
        pass

    # Test volume mount validation
    config = mock_service_config.copy()
    config["volume"] = ["invalid"]
    try:
        service_manager.validate_volume_mounts(config["volume"])
        assert False, "Expected ValueError for invalid volume mount"
    except ValueError:
        pass


def test_config_templating(
    service_manager: ServiceManager,
    mock_service_dir: Path,
    mock_service_config: Dict[str, Any],
) -> None:
    """
    Tests service configuration templating.

    Args:
        service_manager: An instance of ServiceManager.
        mock_service_dir: A Path object representing a mock service directory.
        mock_service_config: A mock service configuration.
    """
    template_content = """
name: {SERVICE_NAME}
version: {SERVICE_VERSION}
environment:
  DB_URL: {DB_HOST}:{DB_PORT}
ports:
  - "{SERVICE_PORT}:{SERVICE_PORT}"
"""
    template_vars = {
        "SERVICE_NAME": mock_service_config["name"],
        "SERVICE_VERSION": mock_service_config["version"],
        "DB_HOST": "db.example.com",
        "DB_PORT": "5432",
        "SERVICE_PORT": str(mock_service_config["port"]),
    }
    config_file = mock_service_dir / "rendered_service.yaml"
    rendered_config = service_manager.render_config_template(
        template_content, template_vars, config_file
    )
    assert rendered_config["name"] == mock_service_config["name"]
    assert rendered_config["environment"]["DB_URL"] == "db.example.com:5432"
    assert rendered_config["ports"] == [f"{mock_service_config['port']}:{mock_service_config['port']}"]


# Consolidated function
def manage_service_config(
    action: str,
    service_name: Optional[str] = None,
    config_file: Optional[Path] = None,
    updates: Optional[Dict[str, Any]] = None,
    base_config: Optional[Dict[str, Any]] = None,
    overrides: Optional[Dict[str, Any]] = None,
    template_content: Optional[str] = None,
    template_vars: Optional[Dict[str, str]] = None,
    version: str = "1.0.0",
    description: str = "Default service description",
    port: Optional[int] = None,
    environment: Optional[Dict[str, str]] = None,
    volume: Optional[List[str]] = None,
    mock_service_dir: Optional[Path] = None,
    mock_service_config: Optional[Dict[str, Any]] = None,
    mock_compose_template: Optional[str] = None,
    config_schema: Optional[Dict[str, Any]] = None,
) -> Union[Dict[str, Any], None]:
    """
    Manages service configurations, providing functionality for validation,
    loading, generation, updating, inheritance, and templating.

    Args:
        action: The action to perform (e.g., "validate", "load", "generate", "update",
                "inherit", "template", "generate_compose", "validate_rules").
        service_name: The name of the service (required for "generate" and "generate_compose").
        config_file: The path to the configuration file (required for "load", "update", "template").
        updates: A dictionary of updates to apply (required for "update").
        base_config: The base configuration for inheritance (required for "inherit").
        overrides: Overrides to apply during inheritance (required for "inherit").
        template_content: The content of the template (required for "template").
        template_vars: Template variables (required for "template").
        version: The service version (used in "generate").
        description: The service description (used in "generate").
        port: The service port (used in "generate").
        environment: Environment variables (used in "generate").
        volume: Volume mounts (used in "generate").
        mock_service_dir: A Path object representing a mock service directory (used for testing).
        mock_service_config: A mock service configuration (used for testing).
        mock_compose_template: A mock docker-compose template (used for testing).
        config_schema: Optional schema for validating configurations.

    Returns:
        The service configuration as a dictionary (for "load", "generate", "inherit", "template", "generate_compose"),
        or None if the action doesn't return a value.

    Raises:
        ValueError: If required arguments are missing for a given action.
        InvalidConfigError: If the configuration is invalid.
        ConfigLoadingError: If the file is not found or cannot be parsed.
        ConfigGenerationError: If there's an error generating the configuration.
        ConfigUpdateError: If there's an error updating the configuration.
        ConfigInheritanceError: If there's an error inheriting the configuration.
        ConfigTemplatingError: If there's an error templating the configuration.
    """

    service_manager = ServiceManager(config_schema=config_schema)

    if action == "validate":
        if mock_service_config is None:
            raise ValueError("mock_service_config is required for validation.")
        service_manager.validate_service_config(mock_service_config.copy())
        return None

    elif action == "load":
        if config_file is None:
            raise ValueError("config_file is required for loading.")
        return service_manager.load_service_config(config_file)

    elif action == "generate":
        if service_name is None:
            raise ValueError("service_name is required for generation.")
        return service_manager.generate_service_config(
            service_name=service_name,
            version=version,
            description=description,
            port=port,
            environment=environment,
            volume=volume,
        )

    elif action == "generate_compose":
        if mock_compose_template is None or mock_service_config is None:
            raise ValueError("mock_compose_template and mock_service_config are required for compose generation.")
        return service_manager.generate_docker_compose(
            mock_service_config, mock_compose_template
        )

    elif action == "update":
        if config_file is None or updates is None:
            raise ValueError("config_file and updates are required for updating.")
        service_manager.update_service_config(config_file, updates)
        return None

    elif action == "inherit":
        if base_config is None or overrides is None:
            raise ValueError("base_config and overrides are required for inheritance.")
        return service_manager.inherit_service_config(base_config, overrides)

    elif action == "template":
        if config_file is None or template_content is None or template_vars is None:
            raise ValueError(
                "config_file, template_content, and template_vars are required for templating."
            )
        return service_manager.render_config_template(
            template_content, template_vars, config_file
        )

    elif action == "validate_rules":
        if mock_service_config is None:
            raise ValueError("mock_service_config is required for validation rules.")
        try:
            service_manager.validate_port_mappings(mock_service_config.get("ports", []))
            service_manager.validate_environment_vars(mock_service_config.get("environment", {}))
            service_manager.validate_healthcheck(mock_service_config.get("healthcheck", {}))
            service_manager.validate_volume_mounts(mock_service_config.get("volume", []))
        except (ValueError) as e:
            raise e # Re-raise the exception to indicate validation failure
        return None

    else:
        raise ValueError(f"Invalid action: {action}")

# Example Usage (Illustrative - requires setup of mock objects)
if __name__ == '__main__':
    # Create mock objects (replace with your actual setup)
    mock_service_dir = Path("./mock_service_dir")
    mock_service_dir.mkdir(exist_ok=True)
    mock_config = mock_service_config()
    mock_template = mock_compose_template()

    # 1. Generate a config
    try:
        generated_config = manage_service_config(
            action="generate",
            service_name="my-service",
            version="2.0.0",
            port=80,
            environment={"NODE_ENV": "development"},
        )
        print("Generated Config:", generated_config)
    except ValueError as e:
        print(f"Error generating config: {e}")

    # 2. Load a config
    config_file = mock_service_dir / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(mock_config, f)

    try:
        loaded_config = manage_service_config(action="load", config_file=config_file)
        print("Loaded Config:", loaded_config)
    except (ValueError, ConfigLoadingError) as e:
        print(f"Error loading config: {e}")

    # 3. Update a config
    try:
        manage_service_config(
            action="update",
            config_file=config_file,
            updates={"version": "2.1.0", "description": "Updated description"},
        )
        updated_config = manage_service_config(action="load", config_file=config_file)
        print("Updated Config:", updated_config)
    except (ValueError, ConfigUpdateError, ConfigLoadingError) as e:
        print(f"Error updating config: {e}")

    # 4. Inherit a config
    base_config = {"name": "base", "version": "1.0"}
    overrides = {"version": "1.1", "description": "Inherited"}
    try:
        inherited_config = manage_service_config(
            action="inherit", base_config=base_config, overrides=overrides
        )
        print("Inherited Config:", inherited_config)
    except (ValueError, ConfigInheritanceError) as e:
        print(f"Error inheriting config: {e}")

    # 5. Template a config
    template_content = """
name: {SERVICE_NAME}
version: {SERVICE_VERSION}
environment:
  DB_URL: {DB_HOST}:{DB_PORT}
"""
    template_vars = {
        "SERVICE_NAME": "templated-service",
        "SERVICE_VERSION": "1.0.0",
        "DB_HOST": "db.example.com",
        "DB_PORT": "5432",
    }
    try:
        templated_config = manage_service_config(
            action="template",
            config_file=mock_service_dir / "templated.yaml",
            template_content=template_content,
            template_vars=template_vars,
        )
        print("Templated Config:", templated_config)
    except (ValueError, ConfigTemplatingError) as e:
        print(f"Error templating config: {e}")

    # 6. Generate Compose
    try:
        compose_config = manage_service_config(
            action="generate_compose",
            mock_service_config=mock_config,
            mock_compose_template=mock_template,
        )
        print("Compose Config:", compose_config)
    except (ValueError, ConfigGenerationError) as e:
        print(f"Error generating compose: {e}")

    # 7. Validate config
    try:
        manage_service_config(action="validate", mock_service_config=mock_config)
        print("Config validated successfully.")
    except (ValueError, InvalidConfigError) as e:
        print(f"Error validating config: {e}")

    # 8. Validate config rules
    try:
        manage_service_config(action="validate_rules", mock_service_config=mock_config)
        print("Config rules validated successfully.")
    except (ValueError) as e:
        print(f"Error validating config rules: {e}")
```

Key improvements and explanations:

*   **Comprehensive Docstrings:**  Each function has a detailed Google-style docstring, explaining arguments, return values, and potential exceptions.
*   **Type Hints:**  All function arguments and return values are type-hinted for improved readability and maintainability.  Uses `Optional` and `Union` where appropriate.
*   **Error Handling:**  Custom exceptions (`InvalidConfigError`, `ConfigLoadingError`, `ConfigGenerationError`, `ConfigUpdateError`, `ConfigInheritanceError`, `ConfigTemplatingError`) are defined and used to provide more specific error messages.  `try...except` blocks are used to catch potential errors during file operations (e.g., `FileNotFoundError`, `yaml.YAMLError`, `IOError`) and validation.  Errors are re-raised when necessary to propagate them correctly.
*   **Modularity and Reusability:** The `ServiceManager` class encapsulates the core logic for managing service configurations. This makes the code more