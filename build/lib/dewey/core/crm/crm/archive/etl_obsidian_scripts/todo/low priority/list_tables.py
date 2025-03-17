from supabase import create_client
import os

# Supabase setup
supabase_url = "https://fjzxtsewrykbrfjzatti.supabase.co"
supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZqenh0c2V3cnlrYnJmanphdHRpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzE3NDE0ODUsImV4cCI6MjA0NzMxNzQ4NX0.faaMQ6bwUHdf5c0SjqUZ7Unr7JW8PtAb_-mG1V9Iang"

def list_tables():
    try:
        supabase = create_client(supabase_url, supabase_key)
        print("Connected to Supabase")

        # Try different table names with different cases
        test_tables = [
            'contacts', 'Contacts', 'CONTACTS',
            'clients', 'Clients', 'CLIENTS',
            'emails', 'Emails', 'EMAILS'
        ]

        print("\nTesting different table names:")
        for table_name in test_tables:
            try:
                result = supabase.table(table_name).select('*').limit(1).execute()
                print(f"\nSuccessfully queried '{table_name}':")
                print(f"- Found {len(result.data)} rows")
                if result.data:
                    print(f"- Columns: {list(result.data[0].keys())}")
            except Exception as e:
                print(f"\nError querying '{table_name}': {str(e)}")

    except Exception as e:
        print(f"Error: {str(e)}")
        print(f"Error type: {type(e)}")

if __name__ == "__main__":
    list_tables() 