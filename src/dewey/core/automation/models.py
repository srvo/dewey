from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from dewey.core.base_script import BaseScript


@runtime_checkable
class PathHandler(Protocol):
    """Protocol for handling paths."""

    def __call__(self, path: str) -> Path:
        """Create a Path object."""
        ...


class DefaultPathHandler:
    """Default class for handling paths using pathlib.Path."""

    def __call__(self, path: str) -> Path:
        """Create a Path object."""
        return Path(path)


@dataclass
class Script(BaseScript):
    """Represents an automation script."""

    name: str
    description: str | None = None
    config: dict[str, Any] | None = None

    def __post_init__(self):
        """Initialize the script."""
        super().__init__(config_section=self.name)

    def run(self) -> None:
        """Run the script.

        Raises:
            NotImplementedError: If the run method is not implemented.

        """
        raise NotImplementedError("The run method must be implemented")

    def execute(self) -> None:
        """Execute the script.

        This method calls the run method, which should be implemented by subclasses.

        Raises:
            NotImplementedError: If the run method is not implemented.

        """
        self.run()


class Service(BaseScript):
    """Represents a service that can be deployed and managed."""

    name: str
    path: Path
    config_path: Path
    containers: list[Any]
    description: str | None = None
    config: dict[str, Any] | None = None
    status: str = "inactive"
    version: str = "1.0.0"

    def __init__(
        self,
        name: str,
        path: str,
        config_path: str,
        containers: list[Any],
        description: str | None = None,
        config: dict[str, Any] | None = None,
        status: str = "inactive",
        version: str = "1.0.0",
        path_handler: PathHandler | None = None,
    ) -> None:
        """Initializes a Service instance.

        Args:
            name: The name of the service.
            path: The path to the service.
            config_path: The path to the service configuration.
            containers: The containers associated with the service.
            description: A description of the service.
            config: The configuration for the service.
            status: The status of the service.
            version: The version of the service.
            path_handler: Handler for creating Path objects.

        """
        super().__init__(config_section=name)
        self.name = name
        self._path_handler: PathHandler = path_handler or DefaultPathHandler()
        self.path: Path = self._path_handler(path)
        self.config_path: Path = self._path_handler(config_path)
        self.containers = containers
        self.description = description
        self.config = config
        self.status = status
        self.version = version

    def to_dict(self) -> dict[str, Any]:
        """Convert the service to a dictionary.

        Returns:
            A dictionary representation of the service.

        """
        return {
            "name": self.name,
            "path": str(self.path),
            "config_path": str(self.config_path),
            "containers": self.containers,
            "description": self.description,
            "config": self.config,
            "status": self.status,
            "version": self.version,
        }

    @classmethod
    def from_dict(
        cls, data: dict[str, Any], path_handler: PathHandler | None = None
    ) -> "Service":
        """Create a service from a dictionary.

        Args:
            data: A dictionary containing the service data.
            path_handler: Handler for creating Path objects.

        Returns:
            A Service instance created from the dictionary.

        """
        _path_handler = path_handler or DefaultPathHandler()
        return cls(
            name=data["name"],
            path=data["path"],
            config_path=data["config_path"],
            containers=data["containers"],
            description=data.get("description"),
            config=data.get("config"),
            status=data.get("status", "inactive"),
            version=data.get("version", "1.0.0"),
            path_handler=_path_handler,
        )

    def run(self) -> None:
        """Runs the service.

        Raises:
            NotImplementedError: If the run method is not implemented.

        """
        raise NotImplementedError("The run method must be implemented")

    def execute(self) -> None:
        """Executes the service.

        This method calls the run method, which should be implemented by subclasses.

        Raises:
            NotImplementedError: If the run method is not implemented.

        """
        self.run()
