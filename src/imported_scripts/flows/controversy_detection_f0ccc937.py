"""Controversy detection flows for monitoring specific companies."""

import logging
import os
from datetime import datetime

import aiohttp
import pandas as pd
from prefect import flow, task


@task(retries=2, persist_result=False)
async def load_companies() -> list[tuple[str, str]]:
    """Load companies and their sectors from CSV."""
    try:
        df = pd.read_csv("../farfalle/data/companies.csv")
        return list(zip(df["company_name"], df["sector"], strict=False))
    except Exception as e:
        logging.exception(f"Error loading companies: {e}")
        return []


@task(retries=2, persist_result=False)
async def search_controversies(company: str, sector: str, searxng_session) -> list:
    """Search for company controversies using SearXNG."""
    base_url = os.getenv("SEARXNG_URL", "http://searxng:8080/search")
    # Include sector in search for more relevant results
    params = {
        "q": f"{company} {sector} controversy scandal investigation",
        "format": "json",
        "time_range": "year",
        "engines": "google,bing,duckduckgo",
        "language": "en",
    }

    try:
        response = await searxng_session.get(base_url, params=params)
        data = await response.json()
        return data.get("results", [])
    except Exception as e:
        logging.exception(f"Error searching controversies for {company}: {e}")
        return []


@task(retries=1, persist_result=False)
async def analyze_controversy(
    text: str,
    company: str,
    sector: str,
    openai_client,
) -> dict:
    """Analyze controversy severity and impact using OpenAI."""
    prompt = f"""
    Analyze the following controversy about {company} (in the {sector} sector). Rate its:
    1. Severity (1-5, where 5 is most severe)
    2. Impact type (e.g., financial, reputational, regulatory)
    3. Stakeholders affected
    4. Potential long-term consequences

    Consider sector-specific implications for {sector} industry.

    Text to analyze: {text}

    Provide your analysis in JSON format with these fields:
    severity, impact_type, stakeholders, consequences, summary
    """

    try:
        response = await openai_client.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a corporate risk analyst specializing in industry-specific risk assessment.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=500,
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        logging.exception(f"Error analyzing controversy for {company}: {e}")
        return {
            "severity": 0,
            "impact_type": "unknown",
            "stakeholders": [],
            "consequences": "Analysis failed",
            "summary": f"Error: {e!s}",
        }


@task(persist_result=True)
async def store_controversy(company: str, sector: str, controversy: dict, db) -> None:
    """Store controversy analysis in database."""
    query = """
    INSERT INTO company_controversies (
        company,
        sector,
        title,
        url,
        severity,
        impact_type,
        stakeholders,
        consequences,
        summary,
        detected_at
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
    """
    try:
        await db.execute(
            query,
            company,
            sector,
            controversy["title"],
            controversy["url"],
            controversy["analysis"]["severity"],
            controversy["analysis"]["impact_type"],
            controversy["analysis"]["stakeholders"],
            controversy["analysis"]["consequences"],
            controversy["analysis"]["summary"],
            datetime.utcnow(),
        )
    except Exception as e:
        logging.exception(f"Error storing controversy for {company}: {e}")


@flow(retries=1)
async def detect_company_controversies(
    company: str,
    sector: str,
    searxng_session,
    openai_client,
    db,
) -> dict:
    """Detect and analyze controversies for a specific company."""
    logging.info(f"Checking controversies for {company} ({sector})")

    controversies = await search_controversies(company, sector, searxng_session)
    if not controversies:
        logging.info(f"No controversies found for {company}")
        return {
            "company": company,
            "sector": sector,
            "status": "no_controversies",
            "details": [],
        }

    analyses = []
    for controversy in controversies[:5]:  # Analyze top 5 controversies
        analysis = await analyze_controversy(
            controversy["snippet"],
            company,
            sector,
            openai_client,
        )
        controversy_data = {
            "title": controversy["title"],
            "url": controversy["url"],
            "analysis": analysis,
        }
        analyses.append(controversy_data)
        await store_controversy(company, sector, controversy_data, db)

    return {
        "company": company,
        "sector": sector,
        "status": "found_controversies",
        "details": sorted(
            analyses,
            key=lambda x: x["analysis"]["severity"],
            reverse=True,
        ),
    }


@flow(retries=1)
async def monitor_all_companies() -> list[dict]:
    """Monitor controversies for all companies in the CSV."""
    companies = await load_companies()
    logging.info(f"Starting controversy monitoring for {len(companies)} companies")

    async with aiohttp.ClientSession() as searxng_session:
        from openai import AsyncOpenAI
        from prefect.blocks.system import Secret

        # Get OpenAI API key from Prefect secret
        openai_key = await Secret.load("openai-api-key")
        openai_client = AsyncOpenAI(api_key=openai_key.get())

        # Get database connection from Prefect block
        from prefect_sqlalchemy import AsyncPostgresEngine

        db = await AsyncPostgresEngine.load("controversy-db")

        results = []
        for company_name, sector in companies:
            result = await detect_company_controversies(
                company_name,
                sector,
                searxng_session,
                openai_client,
                db,
            )
            results.append(result)

        return results


if __name__ == "__main__":
    from prefect.deployments import Deployment
    from prefect.server.schemas.schedules import CronSchedule

    # Create deployment that runs daily at 2 AM UTC
    deployment = Deployment.build_from_flow(
        flow=monitor_all_companies,
        name="daily-controversy-monitor",
        schedule=CronSchedule(cron="0 2 * * *", timezone="UTC"),
        work_queue_name="controversy-monitor",
    )
    deployment.apply()
