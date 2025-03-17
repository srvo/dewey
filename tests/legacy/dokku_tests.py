
# Refactored from: dokku_tests
# Date: 2025-03-16T16:19:09.611051
# Refactor Version: 1.0
#!/usr/bin/env python3

import argparse
import logging
import subprocess
import sys

# Import existing test modules
from dokku.healthcheck import (
    analyze_logs,
    check_port_conflicts,
    check_service_accessibility,
    validate_container_config,
    verify_tailscale_ips,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("test_results.log"),
        logging.StreamHandler(sys.stdout),
    ],
)


class TestRunner:
    def __init__(self, apps=None) -> None:
        self.apps = apps or ["farfalle", "searxng", "minio"]
        self.tailscale_ip = "100.110.141.34"
        self.results = {app: {"passed": 0, "failed": 0} for app in self.apps}

    def run_all_tests(self) -> None:
        """Run all tests for all apps."""
        logging.info("Starting test suite")

        try:
            # Infrastructure tests
            self.test_port_conflicts()
            self.test_tailscale_configuration()

            # App-specific tests
            for app in self.apps:
                self.run_app_tests(app)

            # Generate report
            self.generate_report()

        except Exception as e:
            logging.exception(f"Test suite failed: {e}")
            sys.exit(1)

    def run_app_tests(self, app) -> None:
        """Run all tests for a specific app."""
        logging.info(f"\nTesting {app}")

        # Configuration tests
        self.test_container_config(app)
        self.test_env_vars(app)

        # Health checks
        self.run_dokku_healthcheck(app)

        # Service accessibility
        self.test_service_accessibility(app)

        # Log analysis
        self.analyze_app_logs(app)

    def test_port_conflicts(self) -> None:
        """Check for port conflicts across all apps."""
        logging.info("Checking port conflicts")
        check_port_conflicts()

    def test_container_config(self, app) -> None:
        """Validate container configuration."""
        logging.info(f"Validating {app} configuration")
        expected_config = self.get_expected_config(app)
        validate_container_config(app, expected_config)

    def test_service_accessibility(self, app) -> None:
        """Test service accessibility."""
        logging.info(f"Testing {app} accessibility")
        port = self.get_app_port(app)
        path = self.get_health_path(app)
        check_service_accessibility(app, self.tailscale_ip, port, path)

    def run_dokku_healthcheck(self, app) -> None:
        """Run Dokku's built-in healthchecks."""
        logging.info(f"Running Dokku healthchecks for {app}")
        result = subprocess.run(
            ["ssh", "root@rawls", f"dokku checks:run {app}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            logging.info(f"✅ {app} healthchecks passed")
            self.results[app]["passed"] += 1
        else:
            logging.error(f"❌ {app} healthchecks failed")
            self.results[app]["failed"] += 1

    def test_tailscale_configuration(self) -> None:
        """Verify Tailscale configuration."""
        logging.info("Verifying Tailscale configuration")
        for app in self.apps:
            verify_tailscale_ips(app, self.tailscale_ip)

    def analyze_app_logs(self, app) -> None:
        """Analyze application logs."""
        logging.info(f"Analyzing {app} logs")
        analyze_logs(app)

    def get_expected_config(self, app):
        """Get expected configuration for an app."""
        configs = {
            "farfalle": {
                "NEXT_PUBLIC_API_URL": f"http://{self.tailscale_ip}:3000/api",
                "SEARX_INSTANCE": f"http://{self.tailscale_ip}:3000",
                "OLLAMA_BASE_URL": "http://localhost:11434",
            },
            "searxng": {"SEARXNG_BASE_URL": f"http://{self.tailscale_ip}:3000/"},
            "minio": {"MINIO_BROWSER_REDIRECT_URL": f"http://{self.tailscale_ip}:9000"},
        }
        return configs.get(app, {})

    def get_app_port(self, app):
        """Get the port for an app."""
        ports = {"farfalle": 3000, "searxng": 8080, "minio": 9000}
        return ports.get(app)

    def get_health_path(self, app):
        """Get the health check path for an app."""
        paths = {
            "farfalle": "/api/health",
            "searxng": "/healthz",
            "minio": "/minio/health/live",
        }
        return paths.get(app, "/")

    def generate_report(self) -> None:
        """Generate a test report."""
        logging.info("\nTest Report")
        logging.info("=" * 50)

        total_passed = sum(r["passed"] for r in self.results.values())
        total_failed = sum(r["failed"] for r in self.results.values())

        for app, results in self.results.items():
            logging.info(f"\n{app}:")
            logging.info(f"  Passed: {results['passed']}")
            logging.info(f"  Failed: {results['failed']}")

        logging.info("\nSummary:")
        logging.info(f"Total Passed: {total_passed}")
        logging.info(f"Total Failed: {total_failed}")

        if total_failed > 0:
            sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Dokku infrastructure tests")
    parser.add_argument("--apps", nargs="+", help="Specific apps to test")
    args = parser.parse_args()

    runner = TestRunner(apps=args.apps)
    runner.run_all_tests()


if __name__ == "__main__":
    main()
