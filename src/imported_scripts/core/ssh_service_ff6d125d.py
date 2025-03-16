"""SSH service for remote server management."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import asyncssh

logger = logging.getLogger(__name__)


class SSHError(Exception):
    """SSH service error."""


@dataclass
class ServerInfo:
    """Server information and status."""

    name: str
    host: str
    port: int = 22
    username: str = "root"
    key_path: str | None = None
    services: list[dict] = None

    def __post_init__(self) -> None:
        """Post-initialization to set default services list."""
        self.services = self.services or []


class SSHService:
    """Service for managing SSH connections and remote commands."""

    def __init__(self) -> None:
        """Initialize the SSH service."""
        self.servers: dict[str, ServerInfo] = {}
        self._connections: dict[str, asyncssh.SSHClientConnection] = {}
        self.connected: bool = False
        self.connection: asyncssh.SSHClientConnection | None = None

    async def connect(
        self,
        host: str,
        username: str,
        password: str | None = None,
        key_path: str | None = None,
    ) -> None:
        """Connect to SSH server.

        Args:
        ----
            host: The hostname or IP address of the SSH server.
            username: The username to use for authentication.
            password: The password to use for authentication (optional).
            key_path: The path to the SSH private key file (optional).

        Raises:
        ------
            SSHError: If the connection fails.

        """
        try:
            options: dict[str, str] = {}
            if password:
                options["password"] = password
            if key_path:
                options["client_keys"] = [key_path]

            connection = await asyncssh.connect(host=host, username=username, **options)

            # Only set instance variables after successful connection
            self.connection = connection
            self.connected = True

        except Exception as e:
            msg = f"Failed to connect: {e!s}"
            raise SSHError(msg)

    async def disconnect(self) -> None:
        """Disconnect from SSH server.

        Closes the SSH connection if it exists.
        """
        if self.connection:
            try:
                await self.connection.close()
            except Exception as e:
                logger.exception(f"Error during disconnect: {e!s}")
            finally:
                self.connection = None
                self.connected = False

    async def execute(self, command: str) -> asyncssh.SSHCompletedProcess:
        """Execute a command on the remote server.

        Args:
        ----
            command: The command to execute.

        Returns:
        -------
            The result of the command execution.

        Raises:
        ------
            SSHError: If not connected or command execution fails.

        """
        if not self.connected or not self.connection:
            msg = "Not connected"
            raise SSHError(msg)

        try:
            return await self.connection.run(command)
        except Exception as e:
            msg = f"Failed to execute command: {e!s}"
            raise SSHError(msg)

    async def disconnect_all(self) -> None:
        """Close all SSH connections."""
        for server_name in list(self._connections.keys()):
            await self.disconnect(server_name)

    async def get_services(self, server_name: str) -> list[dict]:
        """Get list of services running on a server.

        Args:
        ----
            server_name: The name of the server.

        Returns:
        -------
            A list of dictionaries, where each dictionary represents a service.
            Returns an empty list if the connection fails or if an error occurs.

        """
        try:
            if not await self.connect(server_name):
                return []

            conn = self._connections[server_name]

            # Get systemd services
            result = await conn.run(
                "systemctl list-units --type=service --no-pager --plain",
            )
            services = self._parse_systemd_services(result.stdout)

            # Get Docker containers
            result = await conn.run(
                'docker ps --format "{{.Names}}\t{{.Status}}\t{{.Ports}}"',
            )
            services.extend(self._parse_docker_services(result.stdout))

            # Update server info
            self.servers[server_name].services = services
            return services

        except Exception as e:
            logger.exception(f"Failed to get services from {server_name}: {e!s}")
            return []

    def _parse_systemd_services(self, output: str) -> list[dict]:
        """Parse systemd service list output.

        Args:
        ----
            output: The output from the systemctl command.

        Returns:
        -------
            A list of dictionaries, where each dictionary represents a systemd service.

        """
        services: list[dict] = []
        for line in output.splitlines():
            if not line.strip() or line.startswith("UNIT"):
                continue

            parts = line.split()
            if len(parts) >= 4:
                unit, load, active, sub, *desc = parts
                if unit.endswith(".service"):
                    services.append(
                        {
                            "name": unit.replace(".service", ""),
                            "type": "systemd",
                            "status": sub,
                            "description": " ".join(desc) if desc else "",
                        },
                    )
        return services

    def _parse_docker_services(self, output: str) -> list[dict]:
        """Parse docker ps output.

        Args:
        ----
            output: The output from the docker ps command.

        Returns:
        -------
            A list of dictionaries, where each dictionary represents a docker service.

        """
        services: list[dict] = []
        for line in output.splitlines():
            if not line.strip():
                continue

            name, status, ports = line.split("\t")
            services.append(
                {"name": name, "type": "docker", "status": status, "ports": ports},
            )
        return services
