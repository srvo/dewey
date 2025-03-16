import os

from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def verify_import() -> None:

    # Check companies count
    supabase.table("companies").select("count", count="exact").execute()

    # Check tick history count
    (supabase.table("tick_history").select("count", count="exact").execute())

    # Check research notes count
    supabase.table("research_notes").select("count", count="exact").execute()

    # Sample some exclusion notes
    exclusions = (
        supabase.table("research_notes")
        .select("ticker,content,created_at")
        .eq("note_type", "exclusion")
        .limit(5)
        .execute()
    )

    for _note in exclusions.data:
        pass


if __name__ == "__main__":
    verify_import()
