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


@task(retries=3, retry_delay_seconds=5)
async def agent_search(entity: str) -> dict:
    """Use Farfalle's agent-based search to analyze an entity."""
    async with httpx.AsyncClient() as client:
        prompt = f"""Please analyze {entity} focusing on:
        1. Major controversies or criticisms
        2. Regulatory issues or investigations
        3. Public perception and reputation
        4. Environmental and social impact
        5. Corporate governance concerns

        For each point, evaluate the credibility of sources and provide context."""

        response = await client.post(
            f"{FARFALLE_API_URL}/chat",
            json={
                "messages": [{"role": "user", "content": prompt}],
                "model": "gpt-4",
                "pro_search": True,  # Enable agent-based search
            },
        )

        if response.status_code == 200:
            return response.json()
        return {"error": "Failed to generate analysis"}


@task
async def extract_key_findings(analysis: dict) -> dict:
    """Extract and categorize key findings from the agent's analysis."""
    async with httpx.AsyncClient() as client:
        prompt = """Please analyze the previous response and extract:
        1. Key controversies identified
        2. Source credibility assessment
        3. Timeline of major events
        4. Current status of issues
        5. Potential future concerns"""

        response = await client.post(
            f"{FARFALLE_API_URL}/chat",
            json={
                "messages": [
                    {"role": "assistant", "content": str(analysis)},
                    {"role": "user", "content": prompt},
                ],
                "model": "gpt-4",
                "pro_search": False,  # Just analysis, no new search
            },
        )

        if response.status_code == 200:
            return response.json()
        return {"error": "Failed to extract findings"}


@flow(name="agent-analysis")
async def analyze_entity_with_agent(entity: str, lookback_days: int = 365) -> dict:
    """Analyze an entity using Farfalle's agent-based search capabilities.

    Args:
        entity: Name of the entity to analyze
        lookback_days: How far back to look for information

    """
    # Perform agent-based search and analysis
    analysis = await agent_search(entity)

    # Extract and structure key findings
    findings = await extract_key_findings(analysis)

    return {
        "entity": entity,
        "analysis_date": datetime.now().isoformat(),
        "lookback_period": f"{lookback_days} days",
        "agent_analysis": analysis,
        "structured_findings": findings,
    }


if __name__ == "__main__":
    # For local testing
    import asyncio

    asyncio.run(analyze_entity_with_agent("Tesla"))
