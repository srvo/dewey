import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from service_manager.service_manager import Service, ServiceManager


@pytest.fixture
def mock_github_config() -> dict[str, Any]:
    """Create mock GitHub configuration."""
    return {
        "owner": "test-owner",
        "repo": "test-repo",
        "token": "test-token",
        "labels": ["service-issue", "automated"],
        "assignees": ["test-user"],
    }


@pytest.fixture
def mock_issue_response() -> dict[str, Any]:
    """Create mock GitHub issue response."""
    return {
        "number": 1,
        "html_url": "https://github.com/test-owner/test-repo/issues/1",
        "title": "Service Alert: test-service",
        "state": "open",
        "created_at": "2024-01-01T12:00:00Z",
        "updated_at": "2024-01-01T12:00:00Z",
        "body": "Service alert detected for test-service",
    }


def test_issue_creation(
    service_manager: ServiceManager,
    mock_service_dir: Path,
    mock_github_config: dict[str, Any],
    mock_issue_response: dict[str, Any],
) -> None:
    """Test GitHub issue creation functionality."""
    service = Service(
        name="test-service",
        path=mock_service_dir / "test-service",
        containers=[],
        config_path=service_manager.local_config_dir / "test-service",
    )

    # Mock GitHub API calls
    def mock_github_request(
        method: str,
        url: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        if method == "POST" and "issues" in url:
            return mock_issue_response
        return {}

    service_manager.github_request = mock_github_request  # type: ignore

    # Test issue creation
    issue = service_manager.create_github_issue(
        service=service,
        title="Service Alert: test-service",
        body="Service alert detected for test-service",
        config=mock_github_config,
    )

    assert issue["number"] == 1
    assert issue["state"] == "open"
    assert "test-service" in issue["title"]


def test_issue_update(
    service_manager: ServiceManager,
    mock_service_dir: Path,
    mock_github_config: dict[str, Any],
    mock_issue_response: dict[str, Any],
) -> None:
    """Test GitHub issue update functionality."""
    service = Service(
        name="test-service",
        path=mock_service_dir / "test-service",
        containers=[],
        config_path=service_manager.local_config_dir / "test-service",
    )

    # Mock GitHub API calls
    def mock_github_request(
        method: str,
        url: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        if method == "PATCH" and "issues/1" in url:
            updated_response = mock_issue_response.copy()
            updated_response["body"] = data["body"]
            updated_response["updated_at"] = datetime.now().isoformat()
            return updated_response
        return {}

    service_manager.github_request = mock_github_request  # type: ignore

    # Test issue update
    updated_issue = service_manager.update_github_issue(
        service=service,
        issue_number=1,
        body="Updated: Service is now healthy",
        config=mock_github_config,
    )

    assert updated_issue["number"] == 1
    assert "healthy" in updated_issue["body"]
    assert updated_issue["updated_at"] > mock_issue_response["updated_at"]


def test_issue_tracking(
    service_manager: ServiceManager,
    mock_service_dir: Path,
    mock_github_config: dict[str, Any],
) -> None:
    """Test GitHub issue tracking functionality."""
    tracking_file = mock_service_dir / "github_issues.json"
    service = Service(
        name="test-service",
        path=mock_service_dir / "test-service",
        containers=[],
        config_path=service_manager.local_config_dir / "test-service",
    )

    # Test issue tracking storage
    issue_data = {
        "number": 1,
        "service": "test-service",
        "created_at": datetime.now().isoformat(),
        "status": "open",
    }

    service_manager.track_github_issue(issue_data, tracking_file)
    assert tracking_file.exists()

    with tracking_file.open() as f:
        tracked_issues = json.load(f)
        assert len(tracked_issues) == 1
        assert tracked_issues[0]["number"] == 1

    # Test issue tracking retrieval
    tracked_issue = service_manager.get_tracked_issue(
        service=service,
        tracking_file=tracking_file,
    )
    assert tracked_issue is not None
    assert tracked_issue["number"] == 1
    assert tracked_issue["service"] == "test-service"


def test_issue_resolution(
    service_manager: ServiceManager,
    mock_service_dir: Path,
    mock_github_config: dict[str, Any],
    mock_issue_response: dict[str, Any],
) -> None:
    """Test GitHub issue resolution functionality."""
    service = Service(
        name="test-service",
        path=mock_service_dir / "test-service",
        containers=[],
        config_path=service_manager.local_config_dir / "test-service",
    )

    # Mock GitHub API calls
    def mock_github_request(
        method: str,
        url: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        if method == "PATCH" and "issues/1" in url:
            resolved_response = mock_issue_response.copy()
            resolved_response["state"] = "closed"
            resolved_response["updated_at"] = datetime.now().isoformat()
            return resolved_response
        return {}

    service_manager.github_request = mock_github_request  # type: ignore

    # Test issue resolution
    resolved_issue = service_manager.resolve_github_issue(
        service=service,
        issue_number=1,
        resolution_message="Service issue has been resolved",
        config=mock_github_config,
    )

    assert resolved_issue["state"] == "closed"
    assert resolved_issue["updated_at"] > mock_issue_response["updated_at"]


def test_issue_comment(
    service_manager: ServiceManager,
    mock_service_dir: Path,
    mock_github_config: dict[str, Any],
) -> None:
    """Test GitHub issue comment functionality."""
    service = Service(
        name="test-service",
        path=mock_service_dir / "test-service",
        containers=[],
        config_path=service_manager.local_config_dir / "test-service",
    )

    # Mock GitHub API calls
    def mock_github_request(
        method: str,
        url: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        if method == "POST" and "issues/1/comments" in url:
            return {
                "id": 1,
                "body": data["body"],
                "created_at": datetime.now().isoformat(),
                "html_url": f"{mock_issue_response['html_url']}#comment-1",
            }
        return {}

    service_manager.github_request = mock_github_request  # type: ignore

    # Test adding comment
    comment = service_manager.add_issue_comment(
        service=service,
        issue_number=1,
        comment="Service status update: Memory usage normalized",
        config=mock_github_config,
    )

    assert comment["id"] == 1
    assert "Memory usage" in comment["body"]
    assert "comment-1" in comment["html_url"]


def test_issue_template(
    service_manager: ServiceManager,
    mock_service_dir: Path,
) -> None:
    """Test GitHub issue template functionality."""
    template_dir = mock_service_dir / ".github" / "ISSUE_TEMPLATE"
    template_dir.mkdir(parents=True, exist_ok=True)

    # Test template generation
    templates = service_manager.generate_issue_templates(template_dir)
    assert len(templates) > 0

    service_template = template_dir / "service_issue.md"
    assert service_template.exists()

    content = service_template.read_text()
    assert "Service Name" in content
    assert "Issue Description" in content
    assert "Current Status" in content
