import os
from datetime import UTC, datetime

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# Initialize Supabase client
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY"),
)


def import_companies() -> None:
    # Read universe.csv
    df = pd.read_csv("/Users/srvo/Development/archive/port/universe.csv")

    # Sort by date if available and take the latest entry for each ticker
    if "Last Tick Date" in df.columns:
        df["Last Tick Date"] = pd.to_datetime(df["Last Tick Date"], errors="coerce")
        df = df.sort_values("Last Tick Date").groupby("Ticker").last().reset_index()

    # Clean and transform data
    companies = []
    seen_tickers = set()  # Track which tickers we've already processed

    for _, row in df.iterrows():
        ticker = row["Ticker"]

        # Skip if ticker is NaN or already seen
        if pd.isna(ticker) or ticker in seen_tickers:
            continue

        seen_tickers.add(ticker)

        # Handle NaN values explicitly
        company = {
            "ticker": ticker,
            "security_name": (
                row["Security Name"] if pd.notna(row["Security Name"]) else None
            ),
            "category": row["Category"] if pd.notna(row["Category"]) else None,
            "sector": row["Sector"] if pd.notna(row["Sector"]) else None,
            "current_tick": int(float(row["Tick"])) if pd.notna(row["Tick"]) else None,
            "excluded": row["Excluded"] == "Exclude",
            "notes": row["Note"] if pd.notna(row["Note"]) else None,
            "created_at": datetime.now(UTC).isoformat(),
            "last_reviewed_at": datetime.now(UTC).isoformat(),
        }
        # Remove None values to prevent JSON issues
        company = {k: v for k, v in company.items() if v is not None}
        companies.append(company)

    # Batch insert into Supabase
    for i in range(0, len(companies), 100):  # Process in batches of 100
        batch = companies[i : i + 100]
        supabase.table("companies").insert(batch).execute()


def import_tick_history() -> None:
    # Read tickhistory.csv
    df = pd.read_csv("/Users/srvo/Development/archive/port/tickhistory.csv")

    # Get company IDs from Supabase
    companies = supabase.table("companies").select("id, ticker").execute()
    company_map = {c["ticker"]: c["id"] for c in companies.data}

    # Clean and transform data
    tick_history = []
    for _, row in df.iterrows():
        if pd.notna(row["Ticker"]) and row["Ticker"] in company_map:
            # Helper function to safely convert tick values
            def safe_tick_convert(value):
                if pd.isna(value) or value in ["PORT", ".", ""]:
                    return None
                try:
                    # Convert to float first, then to integer
                    return int(float(value))
                except (ValueError, TypeError):
                    return None

            history = {
                "company_id": company_map[row["Ticker"]],
                "old_tick": safe_tick_convert(row["Old Tick"]),
                "new_tick": safe_tick_convert(row["New Tick"]),
                "change_date": (
                    pd.to_datetime(row["Date"]).isoformat()
                    if pd.notna(row["Date"])
                    else None
                ),
                "month": int(row["Month"]) if pd.notna(row["Month"]) else None,
                "year": int(row["Year"]) if pd.notna(row["Year"]) else None,
                "created_at": datetime.now(UTC).isoformat(),
            }
            # Remove None values
            history = {k: v for k, v in history.items() if v is not None}
            tick_history.append(history)

    # Batch insert into Supabase
    for i in range(0, len(tick_history), 100):
        batch = tick_history[i : i + 100]
        supabase.table("tick_history").insert(batch).execute()


def import_exclusions() -> None:
    # Read exclude.csv
    df = pd.read_csv("/Users/srvo/Development/archive/port/exclude.csv")

    # Clean and transform data into research notes
    exclusion_notes = []
    for _, row in df.iterrows():
        if pd.notna(row["Symbol"]):  # Only process rows with valid symbols
            # Construct content from available fields
            content_parts = []
            if pd.notna(row["Category"]):
                content_parts.append(f"Category: {row['Category']}")
            if pd.notna(row["Criteria"]):
                content_parts.append(f"Criteria: {row['Criteria']}")
            if pd.notna(row["Concerned groups"]):
                content_parts.append(f"Groups: {row['Concerned groups']}")
            if pd.notna(row["Notes"]):
                content_parts.append(f"Notes: {row['Notes']}")

            # Handle date parsing safely
            created_at = datetime.now(UTC).isoformat()
            if pd.notna(row["Date"]):
                try:
                    # Try to parse date with explicit format and dayfirst=True
                    created_at = pd.to_datetime(
                        row["Date"],
                        format="%d.%m.%Y",
                        dayfirst=True,
                        errors="coerce",
                    )
                    if pd.notna(created_at):
                        created_at = created_at.isoformat()
                    else:
                        created_at = datetime.now(UTC).isoformat()
                except Exception:
                    # If parsing fails, use current timestamp
                    created_at = datetime.now(UTC).isoformat()

            note = {
                "ticker": row["Symbol"],
                "content": " | ".join(content_parts),
                "note_type": "exclusion",
                "created_by": "sloane@ethicic.com",
                "tags": (
                    ["exclusion", row["Category"].lower().replace("-", "_")]
                    if pd.notna(row["Category"])
                    else ["exclusion"]
                ),
                "created_at": created_at,
            }
            exclusion_notes.append(note)

    # Batch insert into Supabase
    for i in range(0, len(exclusion_notes), 100):  # Process in batches of 100
        batch = exclusion_notes[i : i + 100]
        supabase.table("research_notes").insert(batch).execute()


def cleanup_tables() -> None:
    try:
        # Delete all existing records
        supabase.table("tick_history").delete().neq("id", 0).execute()
        supabase.table("research_notes").delete().neq("id", 0).execute()
        supabase.table("companies").delete().neq("id", 0).execute()
    except Exception:
        pass


def main() -> None:

    try:
        # Add cleanup before import
        cleanup_tables()

        import_companies()

        import_tick_history()

        import_exclusions()

    except Exception:
        pass


if __name__ == "__main__":
    main()
