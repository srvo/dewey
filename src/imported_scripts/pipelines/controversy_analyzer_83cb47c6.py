from __future__ import annotations

import os
from datetime import datetime

import httpx
from dotenv import load_dotenv
from prefect import flow, task

load_dotenv()

FARFALLE_API_URL = os.getenv(
    "FARFALLE_API_URL",
    "https://research.sloane-collective.com",
)
SEARXNG_URL = os.getenv("SEARXNG_URL", "https://search.sloane-collective.com")


@task(retries=3, retry_delay_seconds=5)
async def search_controversies(entity: str) -> list[dict]:
    """Search for controversies related to an entity using SearXNG."""
    async with httpx.AsyncClient() as client:
        # Search with specific controversy-related terms
        queries = [
            f"{entity} controversy",
            f"{entity} scandal",
            f"{entity} criticism",
            f"{entity} investigation",
        ]
        results = []

        for query in queries:
            response = await client.get(
                f"{SEARXNG_URL}/search",
                params={"q": query, "format": "json"},
                headers={"Accept": "application/json"},
            )
            if response.status_code == 200:
                data = response.json()
                results.extend(data.get("results", []))

        return results


@task(retries=2)
async def analyze_sources(results: list[dict]) -> dict:
    """Analyze and categorize sources of controversy information."""
    sources = {"news": [], "academic": [], "regulatory": [], "social_media": []}

    for result in results:
        url = result.get("url", "")
        title = result.get("title", "")
        source_type = categorize_source(url)
        if source_type:
            sources[source_type].append(
                {"url": url, "title": title, "date": result.get("published_date", "")},
            )

    return sources


@task
def categorize_source(url: str) -> str | None:
    """Categorize the type of source based on URL patterns."""
    academic_domains = [".edu", "scholar.google", "jstor.org", "academia.edu"]
    news_domains = ["news", "reuters.com", "bloomberg.com", "ft.com", "wsj.com"]
    regulatory_domains = [".gov", "sec.gov", "europa.eu"]
    social_domains = ["twitter.com", "linkedin.com", "facebook.com"]

    url_lower = url.lower()

    if any(domain in url_lower for domain in academic_domains):
        return "academic"
    if any(domain in url_lower for domain in news_domains):
        return "news"
    if any(domain in url_lower for domain in regulatory_domains):
        return "regulatory"
    if any(domain in url_lower for domain in social_domains):
        return "social_media"

    return "news"  # Default to news for other sources


@task
async def summarize_findings(entity: str, sources: dict) -> dict:
    """Use Farfalle's LLM capabilities to summarize findings."""
    async with httpx.AsyncClient() as client:
        prompt = f"""Analyze the following sources about controversies related to {entity}:
        News Sources: {len(sources['news'])}
        Academic Sources: {len(sources['academic'])}
        Regulatory Sources: {len(sources['regulatory'])}
        Social Media Sources: {len(sources['social_media'])}

        Provide a summary of the main controversies and their credibility."""

        response = await client.post(
            f"{FARFALLE_API_URL}/chat",
            json={
                "messages": [{"role": "user", "content": prompt}],
                "model": "gpt-4",
                "pro_search": True,
            },
        )

        if response.status_code == 200:
            return response.json()
        return {"error": "Failed to generate summary"}


@flow(name="controversy-analysis")
async def analyze_entity_controversies(entity: str, lookback_days: int = 365) -> dict:
    """Analyze controversies related to an entity using multiple sources.

    Args:
    ----
        entity: Name of the entity to analyze
        lookback_days: How far back to look for controversies

    """
    # Search for controversies
    search_results = await search_controversies(entity)

    # Analyze and categorize sources
    sources = await analyze_sources(search_results)

    # Generate summary using Farfalle's LLM
    summary = await summarize_findings(entity, sources)

    return {
        "entity": entity,
        "analysis_date": datetime.now().isoformat(),
        "lookback_period": f"{lookback_days} days",
        "sources": sources,
        "summary": summary,
    }


if __name__ == "__main__":
    from prefect.deployments import Deployment
    from prefect.server.schemas.schedules import CronSchedule

    # Create deployment with daily schedule
    deployment = Deployment.build_from_flow(
        flow=analyze_entity_controversies,
        name="daily-controversy-analysis",
        schedule=CronSchedule(cron="0 0 * * *", timezone="UTC"),
        work_queue_name="default",
    )
    deployment.apply()
