"""Relationship Analysis Module

This module provides tools for analyzing and scoring client relationships based on email interactions.
It combines sentiment analysis with interaction frequency to generate relationship quality metrics.

Key Features:
- Sentiment analysis using NLTK's VADER
- Relationship scoring based on sentiment and interaction frequency
- Database integration for storing relationship metrics
- Comprehensive logging and error handling

Dependencies:
- SQLite database with processed contacts
- NLTK's VADER for sentiment analysis
- pandas for data manipulation
- SQLAlchemy for database operations

Typical Usage:
1. Initialize database connection
2. Run assess_relationships() to analyze and score relationships
3. Access relationship metrics through database queries

Note: Ensure NLTK data is downloaded before first use:
    import nltk
    nltk.download('vader_lexicon')
"""

import logging

import pandas as pd
from nltk.sentiment.vader import SentimentIntensityAnalyzer

from scripts.db_connector import get_db

# Configure logging to capture both INFO and ERROR level messages
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="project.log",
    filemode="a",
)
logger = logging.getLogger(__name__)


def sentiment_analysis(text: str) -> float:
    """Perform sentiment analysis on the given text using NLTK's VADER.

    Args:
    ----
        text (str): The text content to analyze. Can be a single message or
                   concatenated messages from a contact.

    Returns:
    -------
        float: A compound sentiment score between -1 (most negative) and 1 (most positive).
               Scores closer to 0 indicate neutral sentiment.

    Example:
    -------
        >>> sentiment_analysis("Great service! Looking forward to more collaborations.")
        0.8316

    """
    # Initialize sentiment analyzer (VADER is optimized for social media text)
    sia = SentimentIntensityAnalyzer()

    # Get sentiment scores (returns dict with pos, neg, neu, and compound scores)
    sentiment = sia.polarity_scores(text)

    # Return compound score which is a normalized, weighted composite
    return sentiment["compound"]


def assess_relationships() -> None:
    """Analyze and score client relationships based on email interactions.

    This function:
    1. Retrieves email interaction data from the database
    2. Calculates sentiment scores for each contact's messages
    3. Computes relationship scores by combining sentiment and interaction frequency
    4. Updates the database with calculated metrics

    The relationship score formula:
        relationship_score = sentiment_score * interaction_count

    Database Updates:
    - Updates 'contacts' table with:
        * relationship_score: Combined metric of sentiment and interaction frequency
        * sentiment_score: Pure sentiment analysis result

    Raises:
    ------
        SQLAlchemyError: If database operations fail
        ValueError: If data processing fails

    """
    # Get database connection
    db = get_db()

    # Query to retrieve email interaction data
    with db.get_connection() as conn:
        query = """
        SELECT
            c.email,
            c.name,
            c.company,
            MAX(e.date) as last_interaction,
            COUNT(e.message_id) as interaction_count,
            GROUP_CONCAT(e.full_message, ' ') as all_messages
        FROM contacts c
        JOIN raw_emails e ON c.email = e.from_email
        JOIN processed_contacts pc ON e.message_id = pc.message_id
        GROUP BY c.email
        """
        # Load data into pandas DataFrame for efficient processing
        df = pd.read_sql_query(query, conn)

    # Calculate sentiment scores for each contact's combined messages
    logger.info("Calculating sentiment scores...")
    df["sentiment_score"] = df["all_messages"].apply(sentiment_analysis)

    # Calculate relationship score by combining sentiment and interaction frequency
    logger.info("Calculating relationship scores...")
    df["relationship_score"] = df["sentiment_score"] * df["interaction_count"]

    # Update database with calculated metrics
    logger.info("Updating database with relationship metrics...")
    with db.get_connection() as conn:
        for _, row in df.iterrows():
            try:
                conn.execute(
                    """
                UPDATE contacts
                SET relationship_score = ?, sentiment_score = ?
                WHERE email = ?
                """,
                    (row["relationship_score"], row["sentiment_score"], row["email"]),
                )
            except Exception as e:
                logger.error(
                    f"Error updating relationship score for {row['email']}: {str(e)}"
                )
                # Continue processing other contacts even if one fails

    logger.info("Completed relationship quality assessment.")


if __name__ == "__main__":
    """
    Main execution block for standalone script operation.
    """
    try:
        logger.info("Starting relationship quality assessment.")
        assess_relationships()
        logger.info("Relationship quality assessment completed successfully.")
    except Exception as e:
        logger.error(f"Relationship assessment failed: {str(e)}")
        raise
