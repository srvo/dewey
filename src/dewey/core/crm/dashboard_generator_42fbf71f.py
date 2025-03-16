```python
"""Script to generate dashboards for visualizing email processing insights.

Dependencies:
- SQLite database with processed contacts and opportunities
- pandas for data manipulation
- seaborn and matplotlib for visualization
"""

import logging
import os

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from scripts.db_connector import get_db

# Initialize logging to capture INFO and ERROR level logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="project.log",
    filemode="a",
)
logger = logging.getLogger(__name__)

DASHBOARD_DIR = "dashboards"


def _ensure_dashboard_directory() -> None:
    """Ensures that the dashboard directory exists.

    Creates the directory if it does not exist.
    """
    if not os.path.exists(DASHBOARD_DIR):
        os.makedirs(DASHBOARD_DIR)


def _fetch_data() -> pd.DataFrame:
    """Fetches data from the database.

    Returns:
        pd.DataFrame: DataFrame containing the fetched data.
    """
    db = get_db()
    with db.get_connection() as conn:
        query = """
        SELECT
            c.company,
            c.relationship_score,
            c.sentiment_score,
            c.demo_opportunity,
            c.cancellation_request,
            c.speaking_opportunity,
            c.publicity_opportunity,
            c.paper_submission_opportunity
        FROM contacts c
        """
        df = pd.read_sql_query(query, conn)
    return df


def _plot_relationship_scores(df: pd.DataFrame) -> None:
    """Plots the distribution of relationship scores.

    Args:
        df: DataFrame containing the relationship scores.
    """
    plt.figure(figsize=(10, 6))
    sns.histplot(df["relationship_score"], bins=20, kde=True, color="skyblue")
    plt.title("Distribution of Relationship Scores")
    plt.xlabel("Relationship Score")
    plt.ylabel("Frequency")
    plt.tight_layout()
    plt.savefig(os.path.join(DASHBOARD_DIR, "relationship_scores.png"))
    plt.close()


def _plot_sentiment_scores(df: pd.DataFrame) -> None:
    """Plots the distribution of sentiment scores.

    Args:
        df: DataFrame containing the sentiment scores.
    """
    plt.figure(figsize=(10, 6))
    sns.histplot(df["sentiment_score"], bins=20, kde=True, color="salmon")
    plt.title("Distribution of Sentiment Scores")
    plt.xlabel("Sentiment Score")
    plt.ylabel("Frequency")
    plt.tight_layout()
    plt.savefig(os.path.join(DASHBOARD_DIR, "sentiment_scores.png"))
    plt.close()


def _plot_business_opportunities(df: pd.DataFrame) -> None:
    """Plots the counts of detected business opportunities.

    Args:
        df: DataFrame containing the opportunity data.
    """
    opportunity_columns = [
        "demo_opportunity",
        "cancellation_request",
        "speaking_opportunity",
        "publicity_opportunity",
        "paper_submission_opportunity",
    ]
    opportunity_counts = df[opportunity_columns].sum().reset_index()
    opportunity_counts.columns = ["Opportunity Type", "Count"]

    plt.figure(figsize=(10, 6))
    sns.barplot(
        data=opportunity_counts,
        x="Opportunity Type",
        y="Count",
        hue="Opportunity Type",
        legend=False,
        palette="viridis",
    )
    plt.title("Detected Business Opportunities")
    plt.xlabel("Opportunity Type")
    plt.ylabel("Count")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(DASHBOARD_DIR, "business_opportunities.png"))
    plt.close()


def create_dashboard() -> None:
    """Creates and saves visualizations for email processing insights.

    Generates histograms for relationship and sentiment scores, and a bar chart
    for detected opportunities.
    """
    logger.info("Starting dashboard creation.")
    _ensure_dashboard_directory()
    df = _fetch_data()
    _plot_relationship_scores(df)
    _plot_sentiment_scores(df)
    _plot_business_opportunities(df)
    logger.info("Dashboard generated successfully.")


if __name__ == "__main__":
    logger.info("Starting dashboard generation.")
    create_dashboard()
    logger.info("Dashboard generation completed successfully.")
```
