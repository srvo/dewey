import shutil
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from service_manager.service_manager import ServiceManager


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """Create a temporary workspace directory."""
    return tmp_path


@pytest.fixture
def service_manager(temp_workspace: Path) -> ServiceManager:
    """Create a ServiceManager instance for testing."""
    return ServiceManager(
        workspace=temp_workspace,
        config_dir=temp_workspace / "config",
        github_token="test-token",
        github_repo="test-owner/test-repo",
    )


@pytest.fixture
def mock_service_dir(temp_workspace: Path) -> Generator[Path, Any, None]:
    """Create a mock service directory with test services."""
    service_dir = temp_workspace / "opt"
    service_dir.mkdir(parents=True)

    # Create test services
    (service_dir / "test-service").mkdir()
    (service_dir / "test-service/docker-compose.yml").write_text(
        """
version: '3'
services:
  test:
    image: nginx:alpine
    ports:
      - "8080:80"
""",
    )

    yield service_dir
    shutil.rmtree(service_dir)
