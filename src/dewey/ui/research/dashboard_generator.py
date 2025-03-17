
# Refactored from: dashboard_generator
# Date: 2025-03-16T16:19:10.183387
# Refactor Version: 1.0
"""Script to generate dashboards for visualizing email processing insights.

Dependencies:
- SQLite database with processed contacts and opportunities
- pandas for data manipulation
- seaborn and matplotlib for visualization
"""

import logging

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from scripts.db_connector import DBConnector

# Initialize logging to capture INFO and ERROR level logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="project.log",
    filemode="a",
)
logger = logging.getLogger(__name__)


def load_data(db: DBConnector) -> pd.DataFrame:
    """Loads data from the database.

    Args:
        db: The database connector.

    Returns:
        A pandas DataFrame containing the loaded data.

    """
    try:
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
            return pd.read_sql_query(query, conn)
    except Exception as e:
        logger.exception(f"Error loading data from database: {e}")
        raise


def plot_distribution(
    data: pd.Series,
    title: str,
    x_label: str,
    filename: str,
    color: str,
) -> None:
    """Plots the distribution of a given data series.

    Args:
        data: The data series to plot.
        title: The title of the plot.
        x_label: The label for the x-axis.
        filename: The filename to save the plot to.
        color: The color of the histogram.

    """
    plt.figure(figsize=(10, 6))
    sns.histplot(data, bins=20, kde=True, color=color)
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel("Frequency")
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()


def plot_opportunity_counts(df: pd.DataFrame, opportunity_columns: list[str]) -> None:
    """Plots the counts of detected business opportunities.

    Args:
        df: The DataFrame containing the opportunity data.
        opportunity_columns: A list of column names representing the different
            opportunity types.

    """
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
    plt.savefig("dashboards/business_opportunities.png")
    plt.close()


def create_dashboard() -> None:
    """Creates and saves visualizations for email processing insights.

    Generates histograms for relationship and sentiment scores, and a bar chart
    for detected opportunities.
    """
    try:
        db = DBConnector()
        df = load_data(db)

        plot_distribution(
            df["relationship_score"],
            "Distribution of Relationship Scores",
            "Relationship Score",
            "dashboards/relationship_scores.png",
            "skyblue",
        )

        plot_distribution(
            df["sentiment_score"],
            "Distribution of Sentiment Scores",
            "Sentiment Score",
            "dashboards/sentiment_scores.png",
            "salmon",
        )

        opportunity_columns = [
            "demo_opportunity",
            "cancellation_request",
            "speaking_opportunity",
            "publicity_opportunity",
            "paper_submission_opportunity",
        ]
        plot_opportunity_counts(df, opportunity_columns)

        logger.info("Dashboard generated successfully.")

    except Exception as e:
        logger.exception(f"Error generating dashboard: {e}")


if __name__ == "__main__":
    logger.info("Starting dashboard generation.")
    create_dashboard()
    logger.info("Dashboard generation completed successfully.")
