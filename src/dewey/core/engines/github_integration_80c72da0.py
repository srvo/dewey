"""GitHub integration for the service manager."""

from __future__ import annotations

from typing import Any

import requests


class GitHubIntegration:
    """GitHub integration for managing service deployments."""

    def __init__(self, token: str, repo: str) -> None:
        """Initialize GitHub integration.

        Args:
        ----
            token: GitHub API token
            repo: GitHub repository (owner/repo)

        """
        self.token = token
        self.repo = repo
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: dict | None = None,
    ) -> dict:
        """Make GitHub API request.

        Args:
        ----
            method: HTTP method
            endpoint: API endpoint
            data: Request data

        Returns:
        -------
            Response data

        """
        url = f"https://api.github.com/repos/{self.repo}/{endpoint}"
        response = requests.request(method, url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

    def create_github_issue(
        self,
        service: str | None,
        title: str,
        description: str,
        config: dict[str, Any],
    ) -> str:
        """Create GitHub issue.

        Args:
        ----
            service: Service name (optional)
            title: Issue title
            description: Issue description
            config: GitHub configuration

        Returns:
        -------
            Issue URL

        """
        data = {"title": title, "body": description, "labels": ["service-manager"]}
        if service:
            data["labels"].append(service)
            data["title"] = f"[{service}] {title}"

        response = self._make_request("POST", "issues", data)
        return response["html_url"]

    def update_github_issue(
        self,
        issue_number: int,
        title: str,
        description: str,
        config: dict[str, Any],
    ) -> dict:
        """Update GitHub issue.

        Args:
        ----
            issue_number: Issue number
            title: Issue title
            description: Issue description
            config: GitHub configuration

        Returns:
        -------
            Updated issue data

        """
        data = {"title": title, "body": description}
        return self._make_request("PATCH", f"issues/{issue_number}", data)

    def resolve_github_issue(
        self,
        issue_number: int,
        resolution: str,
        config: dict[str, Any],
    ) -> dict:
        """Resolve GitHub issue.

        Args:
        ----
            issue_number: Issue number
            resolution: Resolution message
            config: GitHub configuration

        Returns:
        -------
            Updated issue data

        """
        data = {"state": "closed", "state_reason": "completed"}
        self._make_request("PATCH", f"issues/{issue_number}", data)
        self.add_github_comment(issue_number, f"Resolution: {resolution}", config)
        return data

    def add_github_comment(
        self,
        issue_number: int,
        comment: str,
        config: dict[str, Any],
    ) -> dict:
        """Add comment to GitHub issue.

        Args:
        ----
            issue_number: Issue number
            comment: Comment text
            config: GitHub configuration

        Returns:
        -------
            Comment data

        """
        data = {"body": comment}
        return self._make_request("POST", f"issues/{issue_number}/comments", data)

    def get_releases(self):
        """Get list of releases.

        Returns
        -------
            List of release information

        """
        # TODO: Implement GitHub API integration
        return []

    def get_latest_release(self) -> None:
        """Get latest release.

        Returns
        -------
            Latest release information or None

        """
        # TODO: Implement GitHub API integration
        return

    def create_release(self, tag: str, title: str, body: str) -> None:
        """Create a new release.

        Args:
        ----
            tag: Release tag
            title: Release title
            body: Release description

        """
        # TODO: Implement GitHub API integration
