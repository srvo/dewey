from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import aiohttp
import dlt
import pandas as pd
from port5.core.schema_discovery import SchemaDiscovery
from pydantic import BaseModel


# Add new models for security data
class SecurityMetrics(BaseModel):
    """Security metrics for a library."""

    total_vulnerabilities: int
    critical_vulnerabilities: int
    high_vulnerabilities: int
    medium_vulnerabilities: int
    low_vulnerabilities: int
    security_score: float
    last_security_audit: datetime | None
    dependency_health_score: float
    security_policy_exists: bool
    code_signing_enabled: bool


class LibraryTrend(BaseModel):
    """Trend metrics for a library over time."""

    date: datetime
    stars: int | None = None
    commits: int | None = None
    open_issues: int | None = None
    closed_issues: int | None = None
    contributors: int | None = None
    releases: int | None = None
    test_coverage: float | None = None
    documentation_score: float | None = None
    code_quality_score: float | None = None
    security_metrics: SecurityMetrics | None = None


class TechRadarQuadrant(BaseModel):
    """Tech Radar quadrant classification."""

    name: str
    quadrant: str  # ADOPT, TRIAL, ASSESS, HOLD
    ring: int  # 0 (inner) to 3 (outer)
    moved: int  # -1 (moved in), 0 (no move), 1 (moved out)
    description: str
    metrics: dict[str, Any]  # Allow any type for metrics values


async def fetch_github_metrics(session: aiohttp.ClientSession, repo_url: str) -> dict:
    """Fetch metrics from GitHub API for a repository."""
    # Extract owner and repo from URL
    if not repo_url or "github.com" not in repo_url:
        return {}

    try:
        _, _, _, owner, repo = repo_url.rstrip("/").split("/")
        api_url = f"https://api.github.com/repos/{owner}/{repo}"

        # Fetch basic repo info
        async with session.get(api_url) as response:
            if response.status == 404:
                return {}
            if response.status == 403:
                return {
                    "stars": 0,
                    "forks": 0,
                    "open_issues": 0,
                    "closed_issues": 0,
                    "last_commit": None,
                    "license": None,
                    "commits_last_year": 0,
                }
            if response.status != 200:
                return {}

            repo_data = await response.json()

        # Fetch commit activity
        async with session.get(f"{api_url}/stats/commit_activity") as response:
            commit_data = await response.json() if response.status == 200 else []

        # Fetch closed issues count
        async with session.get(f"{api_url}/issues?state=closed&per_page=1") as response:
            closed_issues = int(response.headers.get("X-Total-Count", 0))

        return {
            "stars": repo_data.get("stargazers_count", 0),
            "forks": repo_data.get("forks_count", 0),
            "open_issues": repo_data.get("open_issues_count", 0),
            "closed_issues": closed_issues,
            "last_commit": repo_data.get("pushed_at"),
            "license": repo_data.get("license", {}).get("name"),
            "commits_last_year": (
                sum(week.get("total", 0) for week in commit_data) if commit_data else 0
            ),
        }
    except Exception:
        return {
            "stars": 0,
            "forks": 0,
            "open_issues": 0,
            "closed_issues": 0,
            "last_commit": None,
            "license": None,
            "commits_last_year": 0,
        }


async def fetch_github_metrics_enhanced(session, url, retry_count=0):
    """Fetch metrics with exponential backoff retry."""
    try:
        # Calculate delay with exponential backoff
        delay = min(300, 5 * (2**retry_count))  # Max 5 minutes delay
        await asyncio.sleep(delay)

        # Extract owner and repo from URL
        match = re.search(r"github\.com/([^/]+)/([^/]+)", url)
        if not match:
            return None

        owner, repo = match.groups()
        api_url = f"https://api.github.com/repos/{owner}/{repo}"

        async with session.get(api_url) as response:
            if response.status == 404:
                return None
            if response.status == 429:
                if retry_count < 5:  # Max 5 retries
                    return await fetch_github_metrics_enhanced(
                        session,
                        url,
                        retry_count + 1,
                    )
                return None
            if response.status != 200:
                return None

            data = await response.json()

            # Initialize metrics with default values
            metrics = {
                "stars": int(data.get("stargazers_count", 0)),
                "forks": int(data.get("forks_count", 0)),
                "open_issues": int(data.get("open_issues_count", 0)),
                "closed_issues": 0,
                "contributors": 0,
                "commits_last_year": 0,
                "documentation_score": 0.0,
                "test_coverage": 0.0,
                "dependencies": [],
                "license": data.get("license", {}).get("name", ""),
                "latest_release": "",
                "release_frequency": 0.0,
                "code_velocity": 0.0,
                "issue_resolution_rate": 0.0,
                "security_metrics": {},
                "tech_radar_position": {},
            }

            # Get contributors count with retry
            contributors_url = f"{api_url}/contributors"
            async with session.get(contributors_url) as response:
                if response.status == 200:
                    contributors = await response.json()
                    metrics["contributors"] = len(contributors)
                elif response.status == 429 and retry_count < 5:
                    await asyncio.sleep(delay)
                    return await fetch_github_metrics_enhanced(
                        session,
                        url,
                        retry_count + 1,
                    )

            # Get commit activity with retry
            commits_url = f"{api_url}/stats/commit_activity"
            async with session.get(commits_url) as response:
                if response.status == 200:
                    commit_data = await response.json()
                    if commit_data:
                        metrics["commits_last_year"] = sum(
                            week.get("total", 0) for week in commit_data
                        )
                elif response.status == 429 and retry_count < 5:
                    await asyncio.sleep(delay)
                    return await fetch_github_metrics_enhanced(
                        session,
                        url,
                        retry_count + 1,
                    )

            # Calculate release frequency
            metrics["release_frequency"] = await calculate_release_frequency(
                session,
                owner,
                repo,
            )

            # Calculate metrics
            metrics["code_velocity"] = (
                float(metrics["commits_last_year"]) / 52.0
                if metrics["commits_last_year"] > 0
                else 0.0
            )
            metrics["issue_resolution_rate"] = (
                float(metrics["closed_issues"])
                / (metrics["open_issues"] + metrics["closed_issues"])
                if (metrics["open_issues"] + metrics["closed_issues"]) > 0
                else 0.0
            )

            return metrics

    except Exception:
        return None


async def analyze_test_coverage(session: aiohttp.ClientSession, api_url: str) -> float:
    """Analyze test coverage by checking for test files and their contents."""
    try:
        # Get repository contents
        contents = await session.get(f"{api_url}/contents")
        contents = await contents.json()

        # Look for test directories and files
        test_files = []
        for item in contents:
            name = item.get("name", "").lower()
            if "test" in name or name.startswith("test_"):
                test_files.append(item)

        if not test_files:
            return 0.0

        # Calculate a basic coverage score based on number of test files
        # This is a simple heuristic - could be enhanced with actual coverage data
        return min(len(test_files) * 10, 100) / 100

    except Exception:
        return 0.0


async def analyze_documentation_quality(
    session: aiohttp.ClientSession,
    api_url: str,
) -> float:
    """Analyze documentation quality by checking for documentation files and their contents."""
    try:
        # Get repository contents
        contents = await session.get(f"{api_url}/contents")
        contents = await contents.json()

        # Initialize score components
        has_readme = False
        has_docs_dir = False
        has_examples = False
        has_contributing = False
        has_license = False

        # Check for documentation files
        for item in contents:
            name = item.get("name", "").lower()

            if name == "readme.md":
                has_readme = True
            elif name in ("docs", "documentation"):
                has_docs_dir = True
            elif name == "examples":
                has_examples = True
            elif name == "contributing.md":
                has_contributing = True
            elif name in ("license", "license.md"):
                has_license = True

        # Calculate documentation score
        score = 0.0
        if has_readme:
            score += 0.4  # README is most important
        if has_docs_dir:
            score += 0.3  # Dedicated docs directory
        if has_examples:
            score += 0.1  # Example code
        if has_contributing:
            score += 0.1  # Contributing guidelines
        if has_license:
            score += 0.1  # License file

        return score

    except Exception:
        return 0.0


async def analyze_code_velocity(session: aiohttp.ClientSession, api_url: str) -> dict:
    """Analyze code velocity metrics."""
    async with session.get(f"{api_url}/stats/commit_activity") as response:
        if response.status == 200:
            commit_data = await response.json()
            recent_commits = sum(
                week["total"] for week in commit_data[-4:]
            )  # Last 4 weeks
            return {
                "commits_per_week": recent_commits / 4,
                "active_days": sum(
                    1 for week in commit_data[-4:] for day in week["days"] if day > 0
                ),
            }
    return {"commits_per_week": 0, "active_days": 0}


async def fetch_security_metrics(session: aiohttp.ClientSession, repo_url: str) -> dict:
    """Fetch security metrics from GitHub API for a repository."""
    if not repo_url or "github.com" not in repo_url:
        return {}

    try:
        owner, repo = repo_url.split("/")[-2:]
        api_url = f"https://api.github.com/repos/{owner}/{repo}"

        # Fetch security alerts if available
        alerts_url = f"{api_url}/vulnerability-alerts"
        async with session.get(alerts_url) as response:
            has_vulnerabilities = response.status == 200

        # Check for security policy
        async with session.get(f"{api_url}/contents/SECURITY.md") as response:
            has_security_policy = response.status == 200

        # Check for code signing (look for .sig files in releases)
        async with session.get(f"{api_url}/releases/latest") as response:
            if response.status == 200:
                release = await response.json()
                has_code_signing = any(
                    ".sig" in asset["name"] for asset in release.get("assets", [])
                )
            else:
                has_code_signing = False

        # Calculate security score
        security_score = 0.0
        if not has_vulnerabilities:
            security_score += 0.4  # No known vulnerabilities
        if has_security_policy:
            security_score += 0.3  # Has security policy
        if has_code_signing:
            security_score += 0.3  # Uses code signing

        return {
            "security_metrics": SecurityMetrics(
                total_vulnerabilities=0 if not has_vulnerabilities else 1,
                critical_vulnerabilities=0,
                high_vulnerabilities=0,
                medium_vulnerabilities=0,
                low_vulnerabilities=0,
                security_score=security_score,
                last_security_audit=None,
                dependency_health_score=1.0 if not has_vulnerabilities else 0.5,
                security_policy_exists=has_security_policy,
                code_signing_enabled=has_code_signing,
            ).dict(),
        }

    except Exception:
        return {}


async def analyze_dependency_health(
    session: aiohttp.ClientSession,
    api_url: str,
) -> float:
    """Analyze dependency health based on various factors."""
    try:
        # Check dependency files
        dependency_files = [
            "requirements.txt",
            "package.json",
            "Gemfile",
            "pom.xml",
            "build.gradle",
        ]

        health_score = 0
        max_score = 100

        # Check for dependency files
        for file in dependency_files:
            async with session.get(f"{api_url}/contents/{file}") as response:
                if response.status == 200:
                    health_score += 20  # Points for having dependency file

                    # Check if dependencies are pinned
                    content = await response.json()
                    if content.get("content"):
                        import base64

                        decoded = base64.b64decode(content["content"]).decode()
                        if (
                            "==" in decoded or "@" in decoded
                        ):  # Simple check for version pinning
                            health_score += 10

        # Check for dependency update automation
        async with session.get(
            f"{api_url}/contents/.github/dependabot.yml",
        ) as response:
            if response.status == 200:
                health_score += 30  # Points for having Dependabot

        return min(health_score, max_score)
    except Exception:
        return 0.0


def calculate_tech_radar_position(metrics: dict) -> TechRadarQuadrant:
    """Calculate the position of a library in the tech radar."""
    score = 0
    max_score = 100

    # Update weights to include security
    weights = {
        "stars": 0.15,
        "test_coverage": 0.15,
        "documentation_score": 0.15,
        "code_velocity": 0.15,
        "issue_resolution": 0.15,
        "release_frequency": 0.10,
        "security_score": 0.15,  # Add security weight
    }

    # Calculate normalized scores
    if metrics.get("stars", 0) > 0:
        score += min(metrics["stars"] / 1000, 1) * weights["stars"] * max_score

    if metrics.get("test_coverage"):
        score += metrics["test_coverage"] * weights["test_coverage"] * max_score

    if metrics.get("documentation_score"):
        score += (
            metrics["documentation_score"] * weights["documentation_score"] * max_score
        )

    if metrics.get("code_velocity"):
        velocity_score = min(
            metrics["code_velocity"].get("commits_per_week", 0) / 10,
            1,
        )
        score += velocity_score * weights["code_velocity"] * max_score

    if metrics.get("closed_issues") and metrics.get("open_issues"):
        resolution_rate = metrics["closed_issues"] / (
            metrics["closed_issues"] + metrics["open_issues"]
        )
        score += resolution_rate * weights["issue_resolution"] * max_score

    # Add security score
    if metrics.get("security_metrics"):
        security_score = metrics["security_metrics"].get("security_score", 0)
        score += security_score * weights["security_score"] * max_score

    # Determine quadrant and ring
    if score >= 80:
        quadrant = "ADOPT"
        ring = 0
    elif score >= 60:
        quadrant = "TRIAL"
        ring = 1
    elif score >= 40:
        quadrant = "ASSESS"
        ring = 2
    else:
        quadrant = "HOLD"
        ring = 3

    # Filter metrics to include only numeric values
    filtered_metrics = {
        k: v
        for k, v in metrics.items()
        if isinstance(v, (int, float)) and not isinstance(v, bool)
    }

    return {
        "name": metrics["name"],
        "quadrant": quadrant,
        "ring": ring,
        "moved": 0,
        "description": metrics["description"],
        "metrics": filtered_metrics,
    }


def calculate_release_frequency(releases_data):
    """Calculate the average frequency of releases in days."""
    if not releases_data or len(releases_data) < 2:
        return 0.0

    try:
        # Sort releases by date
        sorted_releases = sorted(releases_data, key=lambda x: x.get("published_at", ""))

        # Calculate time differences between releases
        time_diffs = []
        for i in range(1, len(sorted_releases)):
            prev_date = datetime.fromisoformat(
                sorted_releases[i - 1]["published_at"].replace("Z", "+00:00"),
            )
            curr_date = datetime.fromisoformat(
                sorted_releases[i]["published_at"].replace("Z", "+00:00"),
            )
            diff_days = (curr_date - prev_date).days
            time_diffs.append(diff_days)

        # Calculate average time between releases
        avg_days = sum(time_diffs) / len(time_diffs) if time_diffs else 0

        # Convert to a frequency (releases per month)
        return 30.0 / avg_days if avg_days > 0 else 0.0
    except Exception:
        return 0.0


async def calculate_release_frequency(session, owner, repo, retry_count=0):
    """Calculate release frequency based on release history."""
    try:
        # Calculate delay with exponential backoff
        delay = min(300, 5 * (2**retry_count))  # Max 5 minutes delay
        await asyncio.sleep(delay)

        api_url = f"https://api.github.com/repos/{owner}/{repo}/releases"
        async with session.get(api_url) as response:
            if response.status == 404:
                return 0.0
            if response.status == 429:
                if retry_count < 5:  # Max 5 retries
                    return await calculate_release_frequency(
                        session,
                        owner,
                        repo,
                        retry_count + 1,
                    )
                return 0.0
            if response.status != 200:
                return 0.0

            releases = await response.json()
            if not releases:
                return 0.0

            # Get dates of releases
            dates = []
            for release in releases:
                published_at = release.get("published_at")
                if published_at:
                    try:
                        date = datetime.fromisoformat(
                            published_at.replace("Z", "+00:00"),
                        )
                        dates.append(date)
                    except ValueError:
                        continue

            if len(dates) < 2:
                return 0.0

            # Sort dates in descending order
            dates.sort(reverse=True)

            # Calculate average time between releases in days
            total_days = 0
            for i in range(len(dates) - 1):
                delta = dates[i] - dates[i + 1]
                total_days += delta.days

            avg_days_between_releases = total_days / (len(dates) - 1)

            # Convert to releases per year
            if avg_days_between_releases > 0:
                return 365.0 / avg_days_between_releases
            return 0.0

    except Exception:
        return 0.0


async def main() -> None:
    # Initialize schema discovery and pipeline
    discovery = SchemaDiscovery()
    pipeline = dlt.pipeline(
        pipeline_name="library_metrics",
        destination="duckdb",
        dataset_name="library_analytics",
    )

    # Set up GitHub API headers
    headers = (
        {
            "Authorization": f'token {os.getenv("GITHUB_TOKEN")}',
            "Accept": "application/vnd.github.v3+json",
        }
        if os.getenv("GITHUB_TOKEN")
        else {}
    )

    # Create/load progress tracking file
    progress_file = Path("library_metrics_progress.json")
    if progress_file.exists():
        with open(progress_file) as f:
            processed_libraries = json.load(f)
    else:
        processed_libraries = {}

    async with aiohttp.ClientSession(headers=headers) as session:
        # Process libraries from markdown file
        libraries = await discovery.process_file("libraries_and_resources.md")

        # Initialize lists for storing data
        enriched_data = []
        tech_radar_data = []

        for lib in libraries:
            # Skip if already processed successfully
            if lib.name in processed_libraries and processed_libraries[lib.name].get(
                "success",
                False,
            ):
                enriched_data.append(processed_libraries[lib.name]["metrics"])
                if "tech_radar" in processed_libraries[lib.name]:
                    tech_radar_data.append(processed_libraries[lib.name]["tech_radar"])
                continue

            # Initialize basic data with default values
            metrics = {
                "name": str(lib.name),
                "description": str(
                    lib.sample_values[1] if len(lib.sample_values) > 1 else "",
                ),
                "url": str(lib.sample_values[0] if lib.sample_values else ""),
                "stars": 0,
                "forks": 0,
                "open_issues": 0,
                "closed_issues": 0,
                "contributors": 0,
                "commits_last_year": 0,
                "documentation_score": 0.0,
                "test_coverage": 0.0,
                "dependencies": "[]",
                "license": "",
                "latest_release": "",
                "release_frequency": 0.0,
                "code_velocity": 0.0,
                "issue_resolution_rate": 0.0,
                "security_metrics": "{}",
                "tech_radar_position": "{}",
            }

            success = False
            # The first sample value should be the URL
            if lib.sample_values and "github.com" in lib.sample_values[0]:
                url = lib.sample_values[0]

                github_metrics = await fetch_github_metrics_enhanced(session, url)

                if github_metrics:
                    # Add security metrics with retry
                    security_metrics = await fetch_security_metrics(session, url)
                    if security_metrics:
                        github_metrics.update(security_metrics)

                    # Update metrics with GitHub data
                    for key, value in github_metrics.items():
                        if key in metrics:
                            if isinstance(value, (dict, list)):
                                metrics[key] = json.dumps(value)
                            else:
                                metrics[key] = value

                    # Calculate tech radar position
                    radar_position = calculate_tech_radar_position(metrics)
                    metrics["tech_radar_position"] = json.dumps(radar_position)

                    # Add to tech radar data
                    tech_radar_entry = {
                        "name": str(lib.name),
                        "description": str(metrics["description"]),
                        "ring": str(radar_position.get("ring", "ASSESS")),
                        "quadrant": str(radar_position.get("quadrant", "TOOLS")),
                        "score": float(radar_position.get("score", 0.0)),
                    }
                    tech_radar_data.append(tech_radar_entry)

                    # Mark as successful
                    success = True

                    # Save progress
                    processed_libraries[lib.name] = {
                        "success": True,
                        "metrics": metrics,
                        "tech_radar": tech_radar_entry,
                    }
                    with open(progress_file, "w") as f:
                        json.dump(processed_libraries, f)

            if not success:
                # Save failed attempt
                processed_libraries[lib.name] = {
                    "success": False,
                    "metrics": metrics,
                }
                with open(progress_file, "w") as f:
                    json.dump(processed_libraries, f)

            enriched_data.append(metrics)

            # Store intermediate results every 10 libraries
            if len(enriched_data) % 10 == 0:
                await store_intermediate_results(
                    pipeline,
                    enriched_data,
                    tech_radar_data,
                )

        # Store final results
        await store_intermediate_results(pipeline, enriched_data, tech_radar_data)

        # Print tech radar summary
        for ring in ["ADOPT", "TRIAL", "ASSESS", "HOLD"]:
            ring_libraries = [lib for lib in tech_radar_data if lib["ring"] == ring]
            for lib in ring_libraries:
                pass


async def store_intermediate_results(pipeline, enriched_data, tech_radar_data) -> None:
    """Store intermediate results in DuckDB."""
    if enriched_data:
        # Define column types
        dtypes = {
            "name": "string",
            "description": "string",
            "url": "string",
            "stars": "int64",
            "forks": "int64",
            "open_issues": "int64",
            "closed_issues": "int64",
            "contributors": "int64",
            "commits_last_year": "int64",
            "documentation_score": "float64",
            "test_coverage": "float64",
            "dependencies": "string",
            "license": "string",
            "latest_release": "string",
            "release_frequency": "float64",
            "code_velocity": "float64",
            "issue_resolution_rate": "float64",
            "security_metrics": "string",
            "tech_radar_position": "string",
        }

        df = pd.DataFrame(enriched_data).astype(dtypes)
        pipeline.run(
            df,
            table_name="current_metrics",
            write_disposition="replace",
        )

    if tech_radar_data:
        # Define column types for tech radar data
        radar_dtypes = {
            "name": "string",
            "description": "string",
            "ring": "string",
            "quadrant": "string",
            "score": "float64",
        }

        df = pd.DataFrame(tech_radar_data).astype(radar_dtypes)
        pipeline.run(
            df,
            table_name="tech_radar",
            write_disposition="replace",
        )


if __name__ == "__main__":
    asyncio.run(main())
