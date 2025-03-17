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

from scripts.db_connector import get_db

# Initialize logging to capture INFO and ERROR level logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="project.log",
    filemode="a",
)
logger = logging.getLogger(__name__)


def create_dashboard():
    """Creates and saves visualizations for email processing insights.
    Generates histograms for relationship and sentiment scores, and a bar chart for detected opportunities.
    """
    db = get_db()
    with db.get_connection() as conn:
        # Query to retrieve necessary data for visualization
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

    # Plot distribution of relationship scores
    plt.figure(figsize=(10, 6))
    sns.histplot(df["relationship_score"], bins=20, kde=True, color="skyblue")
    plt.title("Distribution of Relationship Scores")
    plt.xlabel("Relationship Score")
    plt.ylabel("Frequency")
    plt.tight_layout()
    plt.savefig("dashboards/relationship_scores.png")
    plt.close()

    # Plot distribution of sentiment scores
    plt.figure(figsize=(10, 6))
    sns.histplot(df["sentiment_score"], bins=20, kde=True, color="salmon")
    plt.title("Distribution of Sentiment Scores")
    plt.xlabel("Sentiment Score")
    plt.ylabel("Frequency")
    plt.tight_layout()
    plt.savefig("dashboards/sentiment_scores.png")
    plt.close()

    # Plot counts of detected business opportunities
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
    plt.savefig("dashboards/business_opportunities.png")
    plt.close()

    logger.info("Dashboard generated successfully.")


if __name__ == "__main__":
    logger.info("Starting dashboard generation.")
    create_dashboard()
    logger.info("Dashboard generation completed successfully.")
