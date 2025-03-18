
# Refactored from: entity_analyzer
# Date: 2025-03-16T16:19:11.138875
# Refactor Version: 1.0
#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import csv
import json
import logging
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from backend.api.db_manager import DatabaseManager
from backend.api.openrouter_manager import OpenRouterManager


@dataclass
class Source:
    """Represents a source of information about an entity."""

    url: str
    title: str = ""  # Optional title for the source


@dataclass
class EntityAnalysis:
    """Represents the analysis results for an entity."""

    name: str
    has_controversy: bool | None
    controversy_summary: str
    confidence_score: float
    sources: list[str]  # List of source URLs
    sector: str | None = None


class CompanyTracker:
    """Tracks which companies have been analyzed and stores their results."""

    def __init__(self, db_path: str = "company_analysis.db") -> None:
        """Initialize the company tracker with a SQLite database."""
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the SQLite database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS company_analyses (
                    company_name TEXT PRIMARY KEY,
                    sector TEXT,
                    has_controversy BOOLEAN,
                    controversy_summary TEXT,
                    confidence_score REAL,
                    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """,
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_name TEXT,
                    source_url TEXT,
                    FOREIGN KEY(company_name) REFERENCES company_analyses(company_name)
                )
            """,
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_company_name ON analysis_sources(company_name)",
            )

    async def get_analysis(self, company_name: str) -> dict[str, Any] | None:
        """Get the analysis results for a company if it exists."""
        async with asyncio.Lock():

            def _get():
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.execute(
                        "SELECT * FROM company_analyses WHERE company_name = ?",
                        (company_name,),
                    )
                    row = cursor.fetchone()
                    return dict(row) if row else None

            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, _get)

    async def save_analysis(self, analysis: EntityAnalysis) -> None:
        """Save the analysis results for a company."""
        async with asyncio.Lock():

            def _save() -> None:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO company_analyses
                        (company_name, sector, has_controversy, controversy_summary, confidence_score, sources)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            analysis.name,
                            analysis.sector,
                            analysis.has_controversy,
                            analysis.controversy_summary,
                            analysis.confidence_score,
                            json.dumps(list(analysis.sources)),
                        ),
                    )

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _save)

    async def get_all_analyses(self) -> list[dict]:
        """Retrieve all stored analyses."""
        loop = asyncio.get_event_loop()

        def _get_all():
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM company_analyses ORDER BY analysis_date DESC",
                )
                return [dict(row) for row in cursor.fetchall()]

        return await loop.run_in_executor(None, _get_all)


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s:%(message)s",
        handlers=[
            logging.FileHandler("analyze_entities.log"),
            logging.StreamHandler(),
        ],
    )


class EntityAnalyzer:
    """Analyzes entities for controversies using the OpenRouter API."""

    def __init__(self, api_key: str) -> None:
        """Initialize the analyzer with API credentials."""
        db_path = os.getenv("DB_PATH", "api_calls.db")
        self.db_manager = DatabaseManager(db_path)
        self.openrouter = OpenRouterManager(self.db_manager, daily_limit=1000)
        self.tracker = CompanyTracker()
        os.environ["OPENAI_API_KEY"] = api_key
        os.environ["OPENAI_API_BASE"] = os.getenv(
            "OPENAI_API_BASE",
            "https://openrouter.ai/api/v1",
        )

    def _format_prompt(self, entity: str) -> str:
        """Format the prompt for entity analysis."""
        return f"""Please analyze {entity} for any controversies or negative incidents.
        Return a JSON object with the following structure:
        {{
            "has_controversy": boolean,
            "summary": "Brief summary of controversies or 'No significant controversies found'",
            "confidence": float between 0 and 1,
            "sources": [
                {{
                    "url": "URL of source if available, empty string if not",
                    "title": "Title or brief description of source"
                }}
            ]
        }}

        Focus on major controversies like:
        - Legal issues (lawsuits, investigations)
        - Ethical concerns
        - Environmental violations
        - Labor disputes
        - Safety incidents
        - Financial misconduct

        Be objective and factual. Include sources where possible."""

    async def analyze_entity(self, company: str, sector: str) -> EntityAnalysis:
        """Analyze a single company entity for controversies."""
        try:
            cached = await self.tracker.get_analysis(company)
            if cached:
                logging.info(
                    f"Using cached analysis for {company} from {cached['analysis_date']}",
                )
                return EntityAnalysis(
                    name=company,
                    sector=sector,
                    has_controversy=cached["has_controversy"],
                    controversy_summary=cached["controversy_summary"],
                    confidence_score=cached["confidence_score"],
                    sources=cached["sources"],
                )

            logging.info(f"Analyzing {company}...")
            response = await self.openrouter.test_model(
                prompt=self._format_prompt(company),
            )
            analysis = response.get("choices")[0].get("message").get("content")

            # Parse the JSON object from the response
            analysis_data = json.loads(analysis)

            entity_analysis = EntityAnalysis(
                name=company,
                sector=sector,
                has_controversy=analysis_data.get("has_controversy"),
                controversy_summary=analysis_data.get("summary"),
                confidence_score=analysis_data.get("confidence"),
                sources=[
                    source.get("url") for source in analysis_data.get("sources", [])
                ],
            )

            await self.tracker.save_analysis(entity_analysis)
            logging.info(f"Saved analysis for {company}")
            return entity_analysis
        except Exception as e:
            # Log the error and mark the analysis as failed
            logging.exception(f"Error analyzing {company}: {e}")
            return EntityAnalysis(
                name=company,
                sector=sector,
                has_controversy=None,
                controversy_summary=str(e),
                confidence_score=0.0,
                sources=[],
            )

    async def analyze_entities(
        self,
        entities: list[tuple[str, str]],
        output_prefix: str = "analysis_results",
    ) -> list[EntityAnalysis]:
        """Analyze a list of entities for controversies."""
        results = []
        successful = 0
        failed = 0
        with_controversy = 0

        analyzer = EntityAnalyzer()
        for entity, sector in entities:
            try:
                result = await analyzer.analyze_entity(entity, sector)
                if result.has_controversy:
                    with_controversy += 1
                if (
                    result.controversy_summary
                    and not result.controversy_summary.startswith("Error")
                ):
                    successful += 1
                else:
                    failed += 1
                results.append(result)
            except Exception as e:
                failed += 1
                results.append(
                    EntityAnalysis(
                        name=entity,
                        sector=sector,
                        has_controversy=None,
                        controversy_summary=f"Error analyzing {entity}: {e}",
                        confidence_score=0.0,
                        sources=[],
                    ),
                )

        # Save results to JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file = f"{output_prefix}_{timestamp}.json"
        with open(json_file, "w") as f:
            json.dump(
                [
                    {
                        "name": r.name,
                        "sector": r.sector,
                        "has_controversy": r.has_controversy,
                        "controversy_summary": r.controversy_summary,
                        "confidence_score": r.confidence_score,
                        "sources": r.sources,
                    }
                    for r in results
                ],
                f,
                indent=2,
            )

        # Save results to markdown
        md_file = f"{output_prefix}_{timestamp}.md"
        with open(md_file, "w") as f:
            f.write("# Company Controversy Analysis Report\n\n")
            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # Summary section
            f.write("## Summary\n\n")
            f.write(f"- Total companies analyzed: {len(results)}\n")
            f.write(f"- Successful analyses: {successful}\n")
            f.write(f"- Failed analyses: {failed}\n")
            f.write(f"- Companies with controversies: {with_controversy}\n")

            # Quick reference table
            f.write("## Quick Reference\n\n")
            f.write("| Company | Sector | Controversy | Confidence |\n")
            f.write("|---------|---------|-------------|------------|\n")
            for r in results:
                status = (
                    "✅ Yes"
                    if r.has_controversy
                    else (
                        "❌ Error"
                        if not r.controversy_summary
                        or r.controversy_summary.startswith("Error")
                        else "❌ No"
                    )
                )
                f.write(
                    f"| {r.name} | {r.sector or 'N/A'} | {status} | {r.confidence_score:.2f} |\n",
                )

            # Detailed findings
            f.write("\n## Detailed Findings\n\n")
            for r in results:
                f.write(f"### {r.name}\n\n")
                f.write(f"**Sector:** {r.sector or 'N/A'}\n\n")
                f.write(
                    f"**Status:** {'✅ Has Controversy' if r.has_controversy else '❌ No Controversy' if not r.controversy_summary.startswith('Error') else '❌ Analysis Failed'}\n\n",
                )
                f.write(f"**Confidence Score:** {r.confidence_score:.2f}\n\n")
                f.write("**Summary:**\n")
                f.write(f"{r.controversy_summary}\n\n")
                if r.sources:
                    f.write("**Sources:**\n")
                    for s in r.sources:
                        f.write(f"- [{s}]({s})\n")
                f.write("\n---\n\n")

        return results


def read_companies(csv_path: str, limit: int = 25) -> list[tuple[str, str]]:
    """Read companies from CSV file."""
    companies = []
    try:
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= limit:
                    break
                companies.append((row["Company"], row.get("Sector", "")))
    except Exception:
        pass
    return companies


async def main() -> None:
    """Main function to run the analysis."""
    setup_logging()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logging.error("OPENAI_API_KEY environment variable not set")
        return

    analyzer = EntityAnalyzer(api_key)

    # Read companies from CSV
    companies = read_companies(os.getenv("COMPANIES_CSV", "scripts/companies.csv"))
    if not companies:
        logging.warning("No companies found to analyze")
        return

    logging.info(f"Analyzing {len(companies)} companies...")
    results = []

    # Analyze all companies concurrently
    tasks = [analyzer.analyze_entity(company, sector) for company, sector in companies]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save as JSON
    json_path = f"analysis_results_{timestamp}.json"
    with open(json_path, "w") as f:
        json.dump(
            [
                {
                    "name": r.name,
                    "sector": r.sector,
                    "has_controversy": r.has_controversy,
                    "controversy_summary": r.controversy_summary,
                    "confidence_score": r.confidence_score,
                    "sources": list(r.sources),
                }
                for r in results
                if isinstance(r, EntityAnalysis)
            ],
            f,
            indent=2,
        )

    # Save as Markdown
    md_path = f"analysis_results_{timestamp}.md"
    with open(md_path, "w") as f:
        f.write("# Company Controversy Analysis Report\n\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Summary section
        total = len(results)
        controversial = sum(1 for r in results if r.has_controversy)
        failed = sum(1 for r in results if r.has_controversy is None)
        successful = total - failed

        f.write("## Summary\n\n")
        f.write(f"- Total companies analyzed: {total}\n")
        f.write(f"- Successful analyses: {successful}\n")
        f.write(f"- Failed analyses: {failed}\n")
        f.write(f"- Companies with controversies: {controversial}\n")

        # Quick reference table
        f.write("## Quick Reference\n\n")
        f.write("| Company | Sector | Controversy | Confidence |\n")
        f.write("|---------|---------|-------------|------------|\n")
        for r in results:
            if isinstance(r, EntityAnalysis):
                status = (
                    "🚨 Yes"
                    if r.has_controversy
                    else "❌ No" if r.has_controversy is False else "❌ Error"
                )
                f.write(
                    f"| {r.name} | {r.sector or 'N/A'} | {status} | {r.confidence_score:.2f} |\n",
                )

        # Detailed findings
        f.write("\n## Detailed Findings\n\n")
        for r in results:
            if isinstance(r, EntityAnalysis):
                f.write(f"### {r.name}\n\n")
                f.write(f"**Sector:** {r.sector or 'N/A'}\n\n")
                status = (
                    "🚨 Has Controversy"
                    if r.has_controversy
                    else (
                        "✅ No Controversy"
                        if r.has_controversy is False
                        else "❌ Analysis Failed"
                    )
                )
                f.write(f"**Status:** {status}\n\n")
                f.write(f"**Confidence Score:** {r.confidence_score:.2f}\n\n")
                f.write(f"**Summary:**\n{r.controversy_summary}\n\n")
                if r.sources:
                    f.write("**Sources:**\n")
                    for s in r.sources:
                        f.write(f"- [{s}]({s})\n")
                f.write("\n---\n\n")

    logging.info("\nAnalysis complete!")
    logging.info(f"Results saved to {json_path} and {md_path}")


if __name__ == "__main__":
    asyncio.run(main())
