from __future__ import annotations

import duckdb


def analyze_calendar_emails(db_path="contacts.duckdb") -> bool | None:
    try:
        # Connect to both databases
        calendar_con = duckdb.connect("calendar_data.db")
        contacts_con = duckdb.connect(db_path)

        # Create contacts table if it doesn't exist
        contacts_con.execute(
            """
            CREATE TABLE IF NOT EXISTS contacts (
                email VARCHAR,
                name VARCHAR,
                domain VARCHAR,
                source VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        )

        # Get all unique emails from calendar data
        calendar_emails = calendar_con.execute(
            """
            WITH all_emails AS (
                -- Get organizer emails from events
                SELECT DISTINCT organizer_email as email, 'organizer' as source
                FROM calendar_events
                WHERE organizer_email IS NOT NULL
                AND organizer_email != ''

                UNION

                -- Get attendee emails
                SELECT DISTINCT email, 'attendee' as source
                FROM event_attendees
                WHERE email IS NOT NULL
                AND email != ''
            )
            SELECT
                LOWER(TRIM(email)) as email,
                source,
                REGEXP_REPLACE(SPLIT_PART(LOWER(TRIM(email)), '@', 2), '[^a-zA-Z0-9.-]', '') as domain
            FROM all_emails
            WHERE email != ''
            AND REGEXP_MATCHES(email, '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+[.][a-zA-Z]{2,}')
        """,
        ).fetchdf()

        # Get existing contacts with case-insensitive comparison
        existing_contacts = contacts_con.execute(
            """
            SELECT
                LOWER(TRIM(email)) as email,
                name as contact_name,
                domain,
                COUNT(*) as duplicate_count
            FROM contacts
            WHERE email IS NOT NULL
            GROUP BY LOWER(TRIM(email)), name, domain
            HAVING COUNT(*) >= 1
        """,
        ).fetchdf()

        # Check for duplicates within existing contacts
        if not existing_contacts.empty:
            dupes_in_db = contacts_con.execute(
                """
                SELECT
                    LOWER(TRIM(email)) as email,
                    COUNT(*) as count
                FROM contacts
                GROUP BY LOWER(TRIM(email))
                HAVING COUNT(*) > 1
            """,
            ).fetchdf()

            if not dupes_in_db.empty:
                pass

        # Merge to find new contacts (case-insensitive)
        if not existing_contacts.empty:
            merged_df = calendar_emails.merge(
                existing_contacts[["email", "contact_name", "domain"]],
                on="email",
                how="left",
                indicator=True,
            )
            new_contacts = merged_df[merged_df["_merge"] == "left_only"]
        else:
            new_contacts = calendar_emails.copy()

        # Analyze domains
        (new_contacts.groupby("domain").size().sort_values(ascending=False).head(10))

        # Save new contacts to CSV
        if len(new_contacts) > 0:
            output_file = "new_unique_contacts.csv"
            new_contacts[["email", "domain", "source"]].to_csv(output_file, index=False)

            # Sample of new contacts

        # Additional analysis
        new_contacts.groupby("source").size()

        # Optional: Update contacts database with new entries
        should_update = input(
            "\nWould you like to add these new unique contacts to the database? (y/n): ",
        )
        if should_update.lower() == "y":
            # Prepare new contacts for insertion
            new_contacts_for_db = new_contacts[["email", "domain", "source"]].copy()
            new_contacts_for_db["name"] = None

            # Insert directly into contacts table
            contacts_con.execute(
                """
                INSERT INTO contacts (email, domain, name, source)
                SELECT
                    email,
                    domain,
                    name,
                    source
                FROM new_contacts_for_db n
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM contacts c
                    WHERE LOWER(TRIM(c.email)) = LOWER(TRIM(n.email))
                )
            """,
            )

            # Verify the insertion
            contacts_con.execute(
                """
                SELECT COUNT(*) as added_contacts
                FROM contacts
                WHERE LOWER(TRIM(email)) IN (
                    SELECT LOWER(TRIM(email)) FROM new_contacts_for_db
                )
                AND created_at >= CURRENT_TIMESTAMP - INTERVAL 1 MINUTE
            """,
            ).fetchdf()

        # Close connections
        calendar_con.close()
        contacts_con.close()

    except Exception:
        return False


if __name__ == "__main__":
    analyze_calendar_emails()
