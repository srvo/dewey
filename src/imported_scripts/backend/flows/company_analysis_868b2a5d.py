import json
import logging
import sqlite3
from datetime import datetime

from backend.api.db_manager import DatabaseManager
from backend.api.openrouter_manager import OpenRouterManager
from prefect import flow, task
from prefect.artifacts import create_markdown_artifact

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@task
def read_config(config_path: str) -> dict:
    """Read the analysis configuration file."""
    with open(config_path) as f:
        return json.load(f)


@task
def setup_database() -> sqlite3.Connection:
    """Initialize the database connection and ensure schema exists."""
    DB_PATH = "/var/lib/dokku/data/storage/farfalle/company_analysis.db"
    conn = sqlite3.connect(DB_PATH)

    # Create tables if they don't exist
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

    return conn


@task
async def analyze_company_batch(
    companies: list[dict],
    model: str,
    confidence_threshold: float,
    include_sources: bool,
) -> list[dict]:
    """Analyze a batch of companies using the specified model."""
    logger.info(f"Starting analysis of {len(companies)} companies")
    db_manager = DatabaseManager("api_calls.db")
    openrouter = OpenRouterManager(db_manager, daily_limit=1000)

    results = []
    for company in companies:
        try:
            logger.info(f"Analyzing company: {company['Company']}")
            prompt = f"""Please analyze {company['Company']} for any controversies or negative incidents.
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

            try:
                response = await openrouter.test_model(prompt=prompt)
                analysis = json.loads(response["choices"][0]["message"]["content"])

                # Only include results above confidence threshold
                if analysis["confidence"] >= confidence_threshold:
                    result = {
                        "company_name": company["Company"],
                        "sector": company.get("Sector", ""),
                        "has_controversy": analysis["has_controversy"],
                        "controversy_summary": analysis["summary"],
                        "confidence_score": analysis["confidence"],
                        "sources": analysis["sources"] if include_sources else [],
                    }
                    results.append(result)
                    logger.info(
                        f"Successfully analyzed {company['Company']} with confidence {analysis['confidence']}",
                    )
                else:
                    logger.warning(
                        f"Skipping {company['Company']} due to low confidence: {analysis['confidence']}",
                    )
            except json.JSONDecodeError as e:
                logger.exception(
                    f"Failed to parse response for {company['Company']}: {e}",
                )
                continue

        except Exception as e:
            logger.exception(f"Error analyzing {company['Company']}: {e!s}")
            results.append(
                {
                    "company_name": company["Company"],
                    "sector": company.get("Sector", ""),
                    "has_controversy": None,
                    "controversy_summary": f"Error: {e!s}",
                    "confidence_score": 0.0,
                    "sources": [],
                },
            )

    logger.info(f"Completed batch analysis. Processed {len(results)} companies.")
    return results


@task
def save_results(conn: sqlite3.Connection, results: list[dict]) -> None:
    """Save analysis results to the database."""
    cursor = conn.cursor()

    for result in results:
        # Save main analysis
        cursor.execute(
            """
            INSERT OR REPLACE INTO company_analyses
            (company_name, sector, has_controversy, controversy_summary, confidence_score)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                result["company_name"],
                result["sector"],
                result["has_controversy"],
                result["controversy_summary"],
                result["confidence_score"],
            ),
        )

        # Save sources if any
        if result["sources"]:
            cursor.execute(
                "DELETE FROM analysis_sources WHERE company_name = ?",
                (result["company_name"],),
            )
            for source in result["sources"]:
                cursor.execute(
                    """
                    INSERT INTO analysis_sources (company_name, source_url)
                    VALUES (?, ?)
                """,
                    (result["company_name"], source["url"]),
                )

    conn.commit()


@task
def generate_batch_report(results: list[dict]) -> str:
    """Generate a markdown report for the batch results."""
    report = f"""# Batch Analysis Report

Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary
- Companies Analyzed: {len(results)}
- Successful Analyses: {sum(1 for r in results if r['controversy_summary'] and not r['controversy_summary'].startswith('Error'))}
- Failed Analyses: {sum(1 for r in results if r['controversy_summary'].startswith('Error'))}
- Companies with Controversies: {sum(1 for r in results if r['has_controversy'])}

## Details

| Company | Status | Confidence |
|---------|--------|------------|
"""

    for result in results:
        status = "🚨 Has Controversy" if result["has_controversy"] else "✅ No Issues"
        if result["controversy_summary"].startswith("Error"):
            status = "❌ Failed"

        report += f"| {result['company_name']} | {status} | {result['confidence_score']:.2f} |\n"

    return report


@flow(name="Company Analysis Pipeline")
def analyze_companies(config_path: str) -> None:
    """Main flow for analyzing companies."""
    # Read configuration
    config = read_config(config_path)

    # Setup database
    conn = setup_database()

    # Process companies in batches
    companies = config["companies"]
    batch_size = config["parameters"]["batch_size"]

    for i in range(0, len(companies), batch_size):
        batch = companies[i : i + batch_size]

        # Analyze batch
        results = analyze_company_batch(
            companies=batch,
            model=config["parameters"]["model"],
            confidence_threshold=config["parameters"]["confidence_threshold"],
            include_sources=config["parameters"]["include_sources"],
        )

        # Save results
        save_results(conn=conn, results=results)

        # Generate and save batch report
        report = generate_batch_report(results)
        create_markdown_artifact(
            key=f"batch-report-{i//batch_size + 1}",
            markdown=report,
            description=f"Analysis results for batch {i//batch_size + 1}",
        )

    conn.close()


if __name__ == "__main__":
    # For local testing
    analyze_companies("analysis_config_20250101_130417.json")
