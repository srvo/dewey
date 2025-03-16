import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import Service


class ServiceMonitoring:
    """Service monitoring and reporting."""

    def __init__(self, service_manager) -> None:
        """Initialize ServiceMonitoring.

        Args:
        ----
            service_manager: ServiceManager instance

        """
        self.service_manager = service_manager
        self.workspace_dir = service_manager.workspace
        self.config_dir = service_manager.config_dir
        self.reports_dir = self.workspace_dir / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def check_service_health(self, service: Service) -> dict[str, Any]:
        """Check health of a service.

        Args:
        ----
            service: Service to check

        Returns:
        -------
            Dictionary with health check results

        """
        results = {
            "name": service.name,
            "status": "healthy",
            "containers": [],
            "issues": [],
        }

        # Check each container
        for container in service.containers:
            container_health = {
                "name": container.name,
                "status": container.status,
                "health": container.health,
            }

            # Check container status
            if container.status != "running":
                results["status"] = "unhealthy"
                results["issues"].append(
                    f"Container {container.name} is not running (status: {container.status})",
                )

            # Check container health if available
            if container.health and container.health != "healthy":
                results["status"] = "unhealthy"
                results["issues"].append(
                    f"Container {container.name} is not healthy (health: {container.health})",
                )

            # Get container stats
            try:
                stats = self.service_manager.run_command(
                    f"docker stats {container.name} --no-stream --format '{{{{json .}}}}'",
                )
                container_health["stats"] = json.loads(stats)
            except Exception as e:
                container_health["stats"] = None
                results["issues"].append(
                    f"Failed to get stats for {container.name}: {e!s}",
                )

            results["containers"].append(container_health)

        return results

    def generate_service_report(self, service: Service) -> Path:
        """Generate HTML report for a service.

        Args:
        ----
            service: Service to generate report for

        Returns:
        -------
            Path to generated report

        """
        # Get health check results
        health = self.check_service_health(service)

        # Get service logs
        logs = {}
        for container in service.containers:
            try:
                log_output = self.service_manager.run_command(
                    f"docker logs --tail 100 {container.name}",
                )
                logs[container.name] = log_output.splitlines()
            except Exception:
                logs[container.name] = ["Failed to retrieve logs"]

        # Generate HTML report
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        html = f"""
        <html>
        <head>
            <title>Service Report - {service.name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                .status {{ padding: 5px 10px; border-radius: 3px; }}
                .healthy {{ background: #dff0d8; color: #3c763d; }}
                .unhealthy {{ background: #f2dede; color: #a94442; }}
                .container {{ margin: 20px 0; padding: 10px; border: 1px solid #ddd; }}
                .logs {{ background: #f5f5f5; padding: 10px; font-family: monospace; }}
            </style>
        </head>
        <body>
            <h1>Service Report - {service.name}</h1>
            <p>Generated at: {timestamp}</p>

            <h2>Status:
                <span class="status {health['status']}">
                    {health['status'].upper()}
                </span>
            </h2>

            <h3>Issues:</h3>
            <ul>
        """

        for issue in health["issues"]:
            html += f"<li>{issue}</li>"

        html += """
            </ul>

            <h3>Containers:</h3>
        """

        for container in health["containers"]:
            html += f"""
            <div class="container">
                <h4>{container['name']}</h4>
                <p>Status: {container['status']}</p>
                <p>Health: {container['health'] or 'N/A'}</p>

                <h5>Stats:</h5>
                <pre>
                    {json.dumps(container['stats'], indent=2)
                     if container['stats'] else 'N/A'}
                </pre>

                <h5>Logs:</h5>
                <div class="logs">
                    <pre>{'<br>'.join(logs[container['name']])}</pre>
                </div>
            </div>
            """

        html += """
        </body>
        </html>
        """

        # Save report
        report_path = self.reports_dir / f"{service.name}_report.html"
        report_path.write_text(html)

        return report_path

    def update_motd(self, services: list[Service]) -> None:
        """Update MOTD with service status.

        Args:
        ----
            services: List of services to include in MOTD

        """
        motd = ["Service Status Summary:", ""]

        for service in services:
            health = self.check_service_health(service)
            status_icon = "✓" if health["status"] == "healthy" else "✗"

            motd.append(f"{status_icon} {service.name}")
            if health["issues"]:
                for issue in health["issues"]:
                    motd.append(f"  - {issue}")
            motd.append("")

        # Update remote MOTD
        motd_content = "\n".join(motd)
        self.service_manager.run_command(
            f"cat > /etc/motd << 'EOL'\n{motd_content}\nEOL",
        )

    def generate_summary_report(self, services: list[Service]) -> Path:
        """Generate summary report for all services.

        Args:
        ----
            services: List of services to include in report

        Returns:
        -------
            Path to generated report

        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        html = f"""
        <html>
        <head>
            <title>Service Summary Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                .status {{ padding: 5px 10px; border-radius: 3px; }}
                .healthy {{ background: #dff0d8; color: #3c763d; }}
                .unhealthy {{ background: #f2dede; color: #a94442; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ padding: 8px; text-align: left; border: 1px solid #ddd; }}
                th {{ background: #f5f5f5; }}
            </style>
        </head>
        <body>
            <h1>Service Summary Report</h1>
            <p>Generated at: {timestamp}</p>

            <table>
                <tr>
                    <th>Service</th>
                    <th>Status</th>
                    <th>Containers</th>
                    <th>Issues</th>
                </tr>
        """

        for service in services:
            health = self.check_service_health(service)
            status_class = "healthy" if health["status"] == "healthy" else "unhealthy"

            html += f"""
                <tr>
                    <td>{service.name}</td>
                    <td>
                        <span class="status {status_class}">
                            {health['status'].upper()}
                        </span>
                    </td>
                    <td>{len(health['containers'])}</td>
                    <td>{'<br>'.join(health['issues']) or 'None'}</td>
                </tr>
            """

        html += """
            </table>
        </body>
        </html>
        """

        # Save report
        report_path = self.reports_dir / "summary_report.html"
        report_path.write_text(html)

        return report_path

    def monitor_services(self) -> None:
        """Monitor services in real-time."""
        try:
            while True:
                # Clear screen

                # Get all services
                services = self.service_manager.get_services()
                if not services:
                    time.sleep(5)
                    continue

                # Check health of each service
                for service in services:
                    health = self.check_service_health(service)
                    ("\033[92m" if health["status"] == "healthy" else "\033[91m")

                    for container in health["containers"]:
                        if container["stats"]:
                            container["stats"]

                    if health["issues"]:
                        for _issue in health["issues"]:
                            pass

                # Wait before next update
                time.sleep(5)

        except KeyboardInterrupt:
            pass
