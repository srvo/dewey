from __future__ import annotations

import asyncio
import csv
import json
import logging
import os
from datetime import datetime
from typing import Any

from farfalle.src.backend.agent_search import stream_pro_search_objects
from farfalle.src.backend.llm.base import EveryLLM
from farfalle.src.backend.schemas import ChatRequest
from prefect import flow, task

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@task
def read_companies(csv_path: str) -> list[tuple[str, str]]:
    """Read companies from CSV file."""
    companies = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            companies.append((row["Company"], row.get("Sector", "")))
    return companies


@task
async def analyze_company(
    company: str,
    sector: str,
    api_key: str,
    questions: list[str] | None = None,
    datasets: list[str] | None = None,
) -> dict[str, Any]:
    """Analyze a single company for controversies."""
    os.environ["OPENAI_API_KEY"] = api_key
    os.environ["OPENAI_API_BASE"] = "https://openrouter.ai/api/v1"

    llm = EveryLLM(model="openai/gpt-4-turbo-preview")
    request = ChatRequest(
        query=f"Find controversies and issues related to {company} in the {sector} sector",
        model="openai/gpt-4-turbo-preview",
    )

    results = []
    async for event in stream_pro_search_objects(request, llm, request.query, None):
        if event.event == "SEARCH_RESULTS":
            results.extend(event.data.results)

    return {
        "name": company,
        "sector": sector,
        "has_controversy": bool(results),
        "controversy_summary": "\n".join(r.snippet for r in results),
        "confidence_score": len(results)
        / 10,  # Simple scoring based on number of results
        "sources": [{"url": r.url, "title": r.title} for r in results],
    }


@task
def save_results(results: list[dict[str, Any]], output_dir: str) -> None:
    """Save analysis results to JSON and Markdown files."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Save JSON
    json_path = os.path.join(output_dir, f"analysis_results_{timestamp}.json")
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)

    # Save Markdown
    md_path = os.path.join(output_dir, f"analysis_results_{timestamp}.md")
    with open(md_path, "w") as f:
        f.write("# Company Controversy Analysis Report\n\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Add summary and results formatting
        total = len(results)
        controversial = sum(1 for r in results if r.get("has_controversy"))

        f.write("## Summary\n\n")
        f.write(f"- Total companies analyzed: {total}\n")
        f.write(f"- Companies with controversies: {controversial}\n\n")

        for result in results:
            f.write(f"### {result['name']}\n\n")
            f.write(f"**Sector:** {result.get('sector', 'N/A')}\n\n")
            f.write(f"**Has Controversy:** {result['has_controversy']}\n\n")
            f.write(f"**Summary:** {result['controversy_summary']}\n\n")
            if result.get("sources"):
                f.write("**Sources:**\n")
                for source in result["sources"]:
                    f.write(f"- {source}\n")
            f.write("\n---\n\n")


@flow(name="Company Controversy Analysis")
async def analyze_companies_flow(
    csv_path: str = "companies.csv",
    output_dir: str = "analysis_results",
    api_key: str | None = None,
    questions: list[str] | None = None,
    datasets: list[str] | None = None,
    batch_size: int = 5,  # Process companies in smaller batches
):
    """Prefect flow to analyze companies for controversies."""
    logger.info("Starting company analysis flow")

    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            msg = "OpenAI API key not provided"
            raise ValueError(msg)

    # Read companies from CSV
    companies = await read_companies(csv_path)
    logger.info(f"Loaded {len(companies)} companies from {csv_path}")

    # Process companies in batches to avoid overwhelming the API
    results = []
    for i in range(0, len(companies), batch_size):
        batch = companies[i : i + batch_size]
        logger.info(
            f"Processing batch {i//batch_size + 1} of {(len(companies) + batch_size - 1)//batch_size}",
        )

        # Create tasks for the current batch
        tasks = [
            analyze_company(company, sector, api_key, questions, datasets)
            for company, sector in batch
        ]

        # Process batch concurrently
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle results and exceptions
        for result in batch_results:
            if isinstance(result, Exception):
                logger.error(f"Error in batch processing: {result!s}")
                continue
            results.append(result)

        logger.info(
            f"Completed batch {i//batch_size + 1}, processed {len(results)} companies so far",
        )

    # Save results
    try:
        await save_results(results, output_dir)
        logger.info(
            f"Successfully saved results for {len(results)} companies to {output_dir}",
        )
    except Exception as e:
        logger.exception(f"Failed to save results: {e!s}")
        raise

    return results


if __name__ == "__main__":
    asyncio.run(analyze_companies_flow())
