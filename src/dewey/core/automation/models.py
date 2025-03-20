from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from dewey.core.base_script import BaseScript


@dataclass
class Script(BaseScript):
    """Represents an automation script."""

    name: str
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Initialize the script."""
        super().__init__(config_section=self.name)

    def run(self) -> None:
        """
        Run the script.

        Raises:
            NotImplementedError: If the run method is not implemented.
        """
        raise NotImplementedError("The run method must be implemented")


class Service(BaseScript):
    """Represents a service that can be deployed and managed."""

    name: str
    path: Path
    config_path: Path
    containers: List[Any]
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    status: str = "inactive"
    version: str = "1.0.0"

    def __init__(
        self,
        name: str,
        path: Path,
        config_path: Path,
        containers: List[Any],
        description: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        status: str = "inactive",
        version: str = "1.0.0",
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
        """
        super().__init__(config_section=name)
        self.name = name
        self.path = path
        self.config_path = config_path
        self.containers = containers
        self.description = description
        self.config = config
        self.status = status
        self.version = version

    def to_dict(self) -> Dict[str, Any]:
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
    def from_dict(cls, data: Dict[str, Any]) -> "Service":
        """Create a service from a dictionary.

        Args:
            data: A dictionary containing the service data.

        Returns:
            A Service instance created from the dictionary.
        """
        return cls(
            name=data["name"],
            path=Path(data["path"]),
            config_path=Path(data["config_path"]),
            containers=data["containers"],
            description=data.get("description"),
            config=data.get("config"),
            status=data.get("status", "inactive"),
            version=data.get("version", "1.0.0"),
        )

    def run(self) -> None:
        """Runs the service.

        Raises:
            NotImplementedError: If the run method is not implemented.
        """
        raise NotImplementedError("The run method must be implemented")
