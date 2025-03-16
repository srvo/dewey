import re

import duckdb
import pandas as pd


def get_calendar_emails(db_path="contacts.duckdb"):
    """Return a DataFrame of unique emails found in calendar data."""
    try:
        # Connect to DuckDB
        con = duckdb.connect(db_path)

        try:
            # Check if table exists
            table_exists = con.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type='table' AND name='contacts'
            """,
            ).fetchall()

            if not table_exists:
                return pd.DataFrame()

            # Get unique emails only from calendar sources
            df = con.execute(
                """
                WITH CalendarEmails AS (
                    SELECT
                        LOWER(TRIM(email)) as email,
                        name,
                        domain,
                        source,
                        created_at
                    FROM contacts
                    WHERE
                        email IS NOT NULL
                        AND source IN ('organizer', 'attendee')  -- Only calendar sources
                        AND email != ''
                ),
                RankedEmails AS (
                    SELECT
                        *,
                        ROW_NUMBER() OVER (
                            PARTITION BY LOWER(TRIM(email))
                            ORDER BY created_at DESC
                        ) as rn
                    FROM CalendarEmails
                )
                SELECT
                    email,
                    name,
                    domain,
                    source,
                    created_at,
                    (
                        SELECT COUNT(*)
                        FROM contacts c2
                        WHERE LOWER(TRIM(c2.email)) = RankedEmails.email
                        AND c2.source IN ('organizer', 'attendee')
                    ) as calendar_occurrences
                FROM RankedEmails
                WHERE rn = 1
                ORDER BY
                    calendar_occurrences DESC,
                    created_at DESC
            """,
            ).fetchdf()

            # Add metadata columns
            df["is_valid"] = df["email"].apply(
                lambda x: bool(
                    re.match(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+[.][a-zA-Z]{2,}", x),
                ),
            )

            return df

        finally:
            con.close()

    except Exception:
        return pd.DataFrame()


def analyze_calendar_emails(db_path="contacts.duckdb"):
    """Print analysis of unique calendar emails in the database."""
    df = get_calendar_emails(db_path)

    if df.empty:
        return df

    df["domain"].value_counts().head(10)

    df["source"].value_counts()

    return df


if __name__ == "__main__":
    # Get and analyze calendar emails
    df = analyze_calendar_emails()

    # Export to CSV if needed
    # df.to_csv('calendar_emails.csv', index=False)
