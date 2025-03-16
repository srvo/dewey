# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:53:33 2025

"""Script to generate test email data for processing.

This module provides functionality to create realistic test email data for development
and testing purposes. It generates random but structured email content and stores it
in a SQLite database for use in testing email processing pipelines.

The generated data includes:
- Realistic email addresses with name patterns
- Varied job titles and company names
- Random but plausible email content
- Timestamps spread over a 30-day period
- Unique message IDs for each email

The data is stored in the 'enriched_raw_emails' table of the SQLite database.
"""

import random
import sqlite3
import uuid
from datetime import datetime, timedelta

# Sample data pools for generating test emails
# These lists provide realistic values for different email components
COMPANIES = [
    "TechCorp LLC",
    "InnovateNow Inc",
    "DataDrive Solutions",
    "CloudScale Systems",
    "AI Dynamics",
    "Digital Ventures",
    "SmartTech Partners",
    "Future Systems Ltd",
]

JOB_TITLES = [
    "CEO",
    "CTO",
    "Director",
    "Manager",
    "Analyst",
    "Associate",
    "VP",
    "Consultant",
]

DOMAINS = [
    "techcorp.com",
    "innovatenow.io",
    "datadrive.ai",
    "cloudscale.net",
    "aidynamics.com",
    "digitalventures.co",
    "smarttech.com",
    "futuresys.com",
]

SUBJECTS = [
    "Meeting follow-up",
    "Project update",
    "Quick question",
    "Partnership opportunity",
    "Demo request",
    "Introduction",
    "Feedback needed",
    "Touching base",
]


def generate_email_content(name: str, title: str, company: str) -> str:
    """Generate realistic email content with contact information.

    Args:
    ----
        name: Full name of the sender
        title: Job title of the sender
        company: Company name of the sender

    Returns:
    -------
        str: Formatted email content with signature block including:
             - Standard email greeting
             - Generic message body
             - Contact information (name, title, company)
             - Randomly generated phone number
             - LinkedIn profile URL based on name

    """
    return f"""Dear Team,

I wanted to reach out regarding our recent discussion.

Best regards,
{name}
{title} at {company}
Phone: ({random.randint(100, 999)}) {random.randint(100, 999)}-{random.randint(1000, 9999)}
LinkedIn: linkedin.com/in/{name.lower().replace(" ", "")}"""


def generate_test_emails(count: int = 100) -> None:
    """Generate and store test emails in the database.

    Creates a specified number of test emails with realistic data and stores them
    in the SQLite database. Emails are spread over a 30-day period from the current date.

    Args:
    ----
        count: Number of test emails to generate (default: 100)

    Process:
        1. Connects to SQLite database
        2. Generates emails with random but realistic data
        3. Inserts emails in batches of 10
        4. Commits transaction after each batch
        5. Handles errors with rollback on failure

    Database Schema:
        The emails are stored in the 'enriched_raw_emails' table which expects:
        - message_id: Unique identifier (UUID)
        - from_name: Sender's full name
        - from_email: Sender's email address
        - subject: Email subject line
        - full_message: Complete email content
        - date: Timestamp of email
        - created_at: Timestamp of record creation

    """
    # Connect to SQLite database (creates if doesn't exist)
    conn = sqlite3.connect("email_data.db")
    cursor = conn.cursor()

    # Set base time for email timestamps (30 days ago from now)
    base_time = datetime.now() - timedelta(days=30)

    try:
        # Generate specified number of test emails
        for i in range(count):
            # Randomly select company, title, and domain
            company = random.choice(COMPANIES)
            title = random.choice(JOB_TITLES)
            domain = random.choice(DOMAINS)

            # Generate realistic name and email address
            first_name = f"Test{i + 1}"
            last_name = f"User{random.randint(1, 100)}"
            name = f"{first_name} {last_name}"
            email = f"{first_name.lower()}.{last_name.lower()}@{domain}"

            # Generate unique message ID and random timestamp
            message_id = str(uuid.uuid4())
            date = base_time + timedelta(
                days=random.randint(0, 29),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )

            # Insert email record into database
            cursor.execute(
                """
            INSERT INTO enriched_raw_emails (
                message_id, from_name, from_email, subject, full_message, date, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    message_id,
                    name,
                    email,
                    random.choice(SUBJECTS),
                    generate_email_content(name, title, company),
                    date,
                    datetime.now(),
                ),
            )

            # Commit every 10 emails to maintain performance
            if i % 10 == 0:
                conn.commit()

        # Final commit for any remaining emails
        conn.commit()

    except Exception:
        # Handle any errors during generation
        conn.rollback()
    finally:
        # Ensure database connection is closed
        conn.close()


if __name__ == "__main__":
    generate_test_emails()
