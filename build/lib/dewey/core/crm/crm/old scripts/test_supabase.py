from supabase import create_client
import os

# Supabase setup
supabase_url = "https://fjzxtsewrykbrfjzatti.supabase.co"
supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZqenh0c2V3cnlrYnJmanphdHRpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzE3NDE0ODUsImV4cCI6MjA0NzMxNzQ4NX0.faaMQ6bwUHdf5c0SjqUZ7Unr7JW8PtAb_-mG1V9Iang"

def test_connection():
    try:
        # Connect to Supabase
        supabase = create_client(supabase_url, supabase_key)
        print("Connected to Supabase")

        # Try to fetch a single row from Emails table
        result = supabase.table('Emails').select('*').limit(1).execute()
        print(f"Successfully queried Emails table: {len(result.data)} rows")

    except Exception as e:
        print(f"Error: {str(e)}")
        print(f"Error type: {type(e)}")

if __name__ == "__main__":
    test_connection() 