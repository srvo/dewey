
# Refactored from: company_analysis_app
# Date: 2025-03-16T16:19:10.235659
# Refactor Version: 1.0
import marimo as mo

__generated_with = "0.1.0"
app = mo.App()


@app.cell
def imports():
    import json
    import sqlite3
    from datetime import datetime
    from pathlib import Path

    import pandas as pd

    return pd.DataFrame, json, sqlite3, datetime, Path


@app.cell
def intro() -> None:
    mo.md(
        """
    # Company Analysis Data Explorer

    This notebook helps you explore and analyze the company controversy data structure.
    You can:
    - View the latest analysis results
    - Explore trends and patterns
    - Export data for further analysis
    - Monitor database health
    """,
    )


@app.cell
def db_connection(sqlite3):
    DB_PATH = "/var/lib/dokku/data/storage/farfalle/company_analysis.db"
    return sqlite3.connect(DB_PATH)


@app.cell
def load_data(pd, conn):
    # Load main analysis data
    return pd.read_sql(
        """
        SELECT
            ca.company_name,
            ca.sector,
            ca.has_controversy,
            ca.controversy_summary,
            ca.confidence_score,
            ca.analysis_date,
            GROUP_CONCAT(as.source_url) as sources
        FROM company_analyses ca
        LEFT JOIN analysis_sources as ON ca.company_name = as.company_name
        GROUP BY ca.company_name
        ORDER BY ca.analysis_date DESC
    """,
        conn,
    )


@app.cell
def summary_stats(analyses_df) -> None:
    mo.md("## Analysis Summary")

    total = len(analyses_df)
    controversial = analyses_df["has_controversy"].sum()
    avg_confidence = analyses_df["confidence_score"].mean()

    mo.md(
        f"""
    ### Overall Statistics
    - Total Companies Analyzed: {total}
    - Companies with Controversies: {controversial} ({(controversial/total*100):.1f}%)
    - Average Confidence Score: {avg_confidence:.2f}

    ### Latest Analysis
    Last updated: {analyses_df['analysis_date'].max()}
    """,
    )


@app.cell
def sector_breakdown(analyses_df):
    mo.md("## Sector Analysis")

    sector_stats = (
        analyses_df.groupby("sector")
        .agg(
            {
                "company_name": "count",
                "has_controversy": "sum",
                "confidence_score": "mean",
            },
        )
        .round(2)
    )

    sector_stats.columns = ["Total Companies", "With Controversies", "Avg Confidence"]
    return sector_stats


@app.cell
def controversy_details(analyses_df):
    mo.md("## Controversy Details")

    controversial_companies = analyses_df[analyses_df["has_controversy"]].sort_values(
        "confidence_score",
        ascending=False,
    )

    if len(controversial_companies) == 0:
        mo.md("No controversies found in the current dataset.")
        return None

    return controversial_companies[
        ["company_name", "sector", "confidence_score", "controversy_summary", "sources"]
    ]


@app.cell
def data_health(conn) -> None:
    mo.md("## Database Health")

    # Check for potential issues
    cursor = conn.cursor()

    # Check for companies without sources
    no_sources = cursor.execute(
        """
        SELECT COUNT(*) FROM company_analyses ca
        LEFT JOIN analysis_sources as ON ca.company_name = as.company_name
        WHERE as.source_url IS NULL
    """,
    ).fetchone()[0]

    # Check for low confidence scores
    low_confidence = cursor.execute(
        """
        SELECT COUNT(*) FROM company_analyses
        WHERE confidence_score < 0.5
    """,
    ).fetchone()[0]

    mo.md(
        f"""
    ### Data Quality Metrics
    - Companies without sources: {no_sources}
    - Analyses with low confidence: {low_confidence}
    """,
    )


@app.cell
def export_options(analyses_df, json):
    mo.md("## Export Data")

    format_choice = mo.select("Choose export format:", options=["CSV", "JSON", "Excel"])

    if format_choice.value == "CSV":
        analyses_df.to_csv("company_analyses_export.csv", index=False)
        mo.md("Data exported to `company_analyses_export.csv`")
    elif format_choice.value == "JSON":
        analyses_df.to_json("company_analyses_export.json", orient="records", indent=2)
        mo.md("Data exported to `company_analyses_export.json`")
    elif format_choice.value == "Excel":
        analyses_df.to_excel("company_analyses_export.xlsx", index=False)
        mo.md("Data exported to `company_analyses_export.xlsx`")

    return format_choice


if __name__ == "__main__":
    app.run()
