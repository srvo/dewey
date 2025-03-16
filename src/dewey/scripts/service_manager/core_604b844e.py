import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from service_manager.models import Container, Service


class ServiceCore:
    """Core service management functionality."""

    def __init__(self, connection) -> None:
        """Initialize ServiceCore.

        Args:
        ----
            connection: Fabric connection object

        """
        self.connection = connection

    def run_command(self, command: str) -> str:
        """Run a command on the remote host.

        Args:
        ----
            command: Command to run

        Returns:
        -------
            Command output

        """
        try:
            result = self.connection.run(command, hide=True, warn=True)
            if result.failed:
                pass
            return result.stdout.strip()
        except Exception:
            return ""

    def get_services(self) -> list[Service]:
        """Get list of all services.

        Returns
        -------
            List of Service objects

        """
        # Get all running containers first
        cmd = 'docker ps -a --format "{{.Names}}"'
        output = self.run_command(cmd)
        container_names = [line.strip() for line in output.splitlines() if line.strip()]

        # Get service directories from /opt
        output = self.run_command("ls -1 /opt")
        service_dirs = [
            line.strip()
            for line in output.splitlines()
            if line.strip() and line != "service_manager"
        ]

        services = []
        seen_services = set()

        # Add services from running containers
        for name in container_names:
            # Extract service name from container name (e.g. service_web_1 -> service)
            service_name = name.split("_")[0]
            if service_name not in seen_services:
                seen_services.add(service_name)
                service = Service(
                    name=service_name,
                    path=Path("/opt") / service_name,
                    containers=self.find_matching_containers(service_name),
                    config_path=self.config_dir / service_name,
                )
                services.append(service)

        # Add services from /opt that aren't already added
        for service_dir in service_dirs:
            if service_dir not in seen_services:
                seen_services.add(service_dir)
                service = Service(
                    name=service_dir,
                    path=Path("/opt") / service_dir,
                    containers=self.find_matching_containers(service_dir),
                    config_path=self.config_dir / service_dir,
                )
                services.append(service)

        return services

    def find_matching_containers(self, service_name: str) -> list[Container]:
        """Find containers matching a service name.

        Args:
        ----
            service_name: Name of service to find containers for

        Returns:
        -------
            List of Container objects

        """
        # Get running containers with a simpler format first
        cmd = 'docker ps -a --format "{{.Names}}"'
        output = self.run_command(cmd)
        container_names = [name.strip() for name in output.splitlines() if name.strip()]

        containers = []
        service_name_lower = service_name.lower()

        # Filter containers by service name
        matching_names = [
            name for name in container_names if service_name_lower in name.lower()
        ]

        for name in matching_names:
            try:
                # Get container info using inspect
                inspect_cmd = f'docker inspect "{name}"'
                inspect_output = self.run_command(inspect_cmd)
                info = json.loads(inspect_output)[0]

                # Extract relevant information
                status = info["State"]["Status"]
                health = info["State"].get("Health", {}).get("Status")
                image = info["Config"]["Image"]
                started_at = info["State"]["StartedAt"]

                container = Container(
                    name=name,
                    status=status,
                    image=image,
                    health=health,
                    started_at=started_at,
                )
                containers.append(container)
            except (Exception, json.JSONDecodeError, KeyError):
                pass

        return containers

    def get_logs(self, service_name: str, tail: int = 100, follow: bool = False) -> str:
        """Get logs for a service.

        Args:
        ----
            service_name: Name of service to get logs for
            tail: Number of lines to show from end of logs
            follow: Whether to follow log output

        Returns:
        -------
            Service logs

        """
        containers = self.find_matching_containers(service_name)
        if not containers:
            return "No containers found for service"

        logs = []
        for container in containers:
            try:
                cmd = f"docker logs --tail {tail}"
                if follow:
                    cmd += " -f"
                cmd += f' "{container.name}"'
                container_logs = self.run_command(cmd)
                logs.append(f"=== {container.name} ===\n{container_logs}")
            except Exception as e:
                logs.append(f"=== {container.name} ===\nFailed to retrieve logs: {e}")

        return "\n\n".join(logs)

    def control_service(self, service_name: str, action: str) -> bool:
        """Control a service.

        Args:
        ----
            service_name: Name of service to control
            action: Action to perform (start/stop/restart)

        Returns:
        -------
            True if successful, False otherwise

        """
        containers = self.find_matching_containers(service_name)
        if not containers:
            return False

        try:
            for container in containers:
                self.run_command(f'docker {action} "{container.name}"')
            return True
        except Exception:
            return False

    def get_service_status(self, service_name: str) -> dict[str, Any]:
        """Get detailed status of a service.

        Args:
        ----
            service_name: Name of service to get status for

        Returns:
        -------
            Dictionary with service status information

        """
        containers = self.find_matching_containers(service_name)
        if not containers:
            return {"error": "No containers found"}

        status = {
            "name": service_name,
            "containers": [],
        }

        for container in containers:
            try:
                # Get detailed container info
                inspect_cmd = f'docker inspect "{container.name}"'
                inspect_output = self.run_command(inspect_cmd)
                info = json.loads(inspect_output)[0]

                # Get container stats
                stats_cmd = f'docker stats "{container.name}" --no-stream --format "{{{{json .}}}}"'
                stats_output = self.run_command(stats_cmd)
                stats = json.loads(stats_output)

                container_info = {
                    "name": container.name,
                    "status": container.status,
                    "health": container.health,
                    "image": container.image,
                    "state": info["State"],
                    "config": info["Config"],
                    "network": info["NetworkSettings"],
                    "stats": stats,
                }
                status["containers"].append(container_info)
            except Exception as e:
                status["containers"].append(
                    {
                        "name": container.name,
                        "error": str(e),
                    },
                )

        return status

    def sync_service_config(self, service: Service) -> None:
        """Sync service configuration from remote to local.

        Args:
        ----
            service: Service to sync configuration for

        """
        # Create local config directory
        service.config_path.mkdir(parents=True, exist_ok=True)

        # Copy docker-compose.yml
        service.path / "docker-compose.yml"
        local_compose = service.config_path / "docker-compose.yml"

        try:
            with self.connection.cd(str(service.path)):
                compose_content = self.run_command("cat docker-compose.yml")
                local_compose.write_text(compose_content)
        except Exception:
            # File may not exist yet
            pass

    def analyze_services(self) -> dict[str, Any]:
        """Analyze all services.

        Returns
        -------
            Dictionary with analysis results

        """
        services = self.get_services()
        results = {}

        for service in services:
            # Get container stats
            stats = {}
            for container in service.containers:
                try:
                    stats_cmd = f'docker stats "{container.name}" --no-stream --format "{{{{json .}}}}"'
                    stats_output = self.run_command(stats_cmd)
                    stats[container.name] = json.loads(stats_output)
                except Exception:
                    continue

            # Get service logs
            logs = {}
            for container in service.containers:
                try:
                    log_output = self.run_command(
                        f'docker logs --tail 100 "{container.name}"',
                    )
                    logs[container.name] = log_output.splitlines()
                except Exception:
                    continue

            results[service.name] = {
                "containers": [vars(c) for c in service.containers],
                "stats": stats,
                "logs": logs,
            }

        return results

    def verify_configs(self, service: Service) -> dict[str, Any]:
        """Verify service configurations and check for sync status.

        Args:
        ----
            service: Service to verify configurations for

        Returns:
        -------
            Dictionary containing verification results

        """
        results = {
            "compose_file": {"exists": False, "in_sync": False},
            "cloudflare": {"exists": False, "in_sync": False},
            "volumes": [],
            "networks": [],
            "env_vars": [],
        }

        # Check local compose file
        local_compose = service.config_path / "docker-compose.yml"
        if local_compose.exists():
            results["compose_file"]["exists"] = True

            # Check if remote compose file exists and compare
            try:
                with self.connection.cd(str(service.path)):
                    remote_content = self.run_command("cat docker-compose.yml")
                    local_content = local_compose.read_text()
                    results["compose_file"]["in_sync"] = (
                        remote_content.strip() == local_content.strip()
                    )
            except Exception:
                results["compose_file"]["in_sync"] = False

        # Check Cloudflare config
        try:
            local_cf = service.config_path / "config" / "cloudflare.yml"
            if local_cf.exists():
                results["cloudflare"]["exists"] = True
                with self.connection.cd(str(service.path)):
                    if (
                        self.run_command(
                            "test -f config/cloudflare.yml && echo 'true' || echo 'false'",
                        ).strip()
                        == "true"
                    ):
                        remote_content = self.run_command("cat config/cloudflare.yml")
                        local_content = local_cf.read_text()
                        results["cloudflare"]["in_sync"] = (
                            remote_content.strip() == local_content.strip()
                        )
        except Exception:
            pass

        # Get container info
        try:
            containers = self.find_matching_containers(service.name)
            if containers:
                container = containers[0]
                inspect_cmd = f'docker inspect "{container.name}"'
                inspect_output = self.run_command(inspect_cmd)
                container_info = json.loads(inspect_output)[0]

                # Check volumes
                for mount in container_info.get("Mounts", []):
                    results["volumes"].append(
                        {
                            "source": mount.get("Source"),
                            "destination": mount.get("Destination"),
                        },
                    )

                # Check networks
                results["networks"] = list(
                    container_info.get("NetworkSettings", {})
                    .get("Networks", {})
                    .keys(),
                )

                # Check environment variables (excluding sensitive info)
                env_vars = container_info.get("Config", {}).get("Env", [])
                results["env_vars"] = [
                    var
                    for var in env_vars
                    if not any(
                        sensitive in var.split("=")[0].upper()
                        for sensitive in ["PASSWORD", "KEY", "TOKEN", "SECRET"]
                    )
                ]
        except Exception:
            pass

        return results

    def sync_configs(self, service: Service) -> bool:
        """Sync service configurations between local and remote.

        Args:
        ----
            service: Service to sync configurations for

        Returns:
        -------
            True if successful, False otherwise

        """
        try:
            # Create local config directory
            service.config_path.mkdir(parents=True, exist_ok=True)

            # Sync from remote to local
            with self.connection.cd(str(service.path)):
                # Get all config files
                result = self.connection.run("tar czf - .", hide=True)
                if not hasattr(result, "stdout_bytes"):
                    result.stdout_bytes = result.stdout.encode("utf-8")

            # Extract to local config directory
            with tempfile.NamedTemporaryFile() as temp:
                temp.write(result.stdout_bytes)
                temp.flush()
                subprocess.run(
                    ["tar", "xzf", temp.name],
                    cwd=service.config_path,
                    check=True,
                )

            return True
        except Exception:
            return False
