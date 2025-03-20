#!/usr/bin/env python3

import base64
import json
import os

import pytest


@pytest.fixture(scope="session")
def service_urls() -> dict[str, str]:
    """Get service URLs from environment or default to Tailscale IPs."""
    tailscale_ip = os.getenv("TAILSCALE_IP", "100.110.141.34")

    return {
        "farfalle": os.getenv("FARFALLE_URL", f"http://{tailscale_ip}:3000"),
        "searxng": os.getenv("SEARXNG_URL", f"http://{tailscale_ip}:8080"),
        "minio": os.getenv("MINIO_URL", f"http://{tailscale_ip}:9000"),
    }


@pytest.fixture(scope="session")
def auth_headers() -> dict[str, str]:
    """Get authentication headers."""
    username = os.getenv("DOKKU_AUTH_USER", "srvo")
    password = os.getenv("DOKKU_AUTH_PASSWORD", "")

    if not password:
        token = os.getenv("DOKKU_AUTH_TOKEN", "")
        if token:
            return {"Authorization": f"Bearer {token}"}

    auth_string = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {auth_string}"}


@pytest.fixture(scope="session")
def minio_credentials() -> dict[str, str]:
    """Get MinIO credentials."""
    return {
        "access_key": os.getenv("MINIO_ACCESS_KEY"),
        "secret_key": os.getenv("MINIO_SECRET_KEY"),
    }


@pytest.fixture(autouse=True)
def setup_logging(request) -> None:
    """Set up test logging."""
    return


def pytest_configure(config) -> None:
    """Configure pytest markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")


def pytest_collection_modifyitems(config, items) -> None:
    """Modify test collection based on markers."""
    if config.getoption("--skip-integration", default=False):
        skip_integration = pytest.mark.skip(reason="Integration tests skipped")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)


def pytest_addoption(parser) -> None:
    """Add custom command line options."""
    parser.addoption(
        "--skip-integration",
        action="store_true",
        default=False,
        help="Skip integration tests",
    )


@pytest.fixture(scope="session")
def test_data_dir(tmp_path_factory):
    """Create and return a temporary directory for test data."""
    return tmp_path_factory.mktemp("test_data")


@pytest.fixture(scope="session")
def load_test_config():
    """Load test configuration from file."""
    config_path = os.path.join(os.path.dirname(__file__), "test_config.json")
    if os.path.exists(config_path):
        with open(config_path) as f:
            return json.load(f)
    return {}
