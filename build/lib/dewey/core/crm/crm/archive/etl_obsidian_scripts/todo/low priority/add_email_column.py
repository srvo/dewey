from supabase_client import SupabaseClient
import sys

def add_email_column():
    try:
        client = SupabaseClient().get_client()
        print("Connected to Supabase")
        
        # First check what columns exist
        result = client.table('Emails').select('*').limit(1).execute()
        print("\nCurrent columns:", list(result.data[0].keys()))
        
        # Add the column via raw SQL since alter isn't supported in postgrest
        sql = """
        ALTER TABLE "Emails" 
        ADD COLUMN IF NOT EXISTS from_email VARCHAR(255);
        """
        
        response = client.query(sql).execute()
        print("\nAdded from_email column")
        
        return True
            
    except Exception as e:
        print(f"Error: {str(e)}")
        print(f"Error type: {type(e)}")
        return False

if __name__ == "__main__":
    if add_email_column():
        print("\nColumn added successfully!")
        sys.exit(0)
    else:
        print("\nFailed to add column")
        sys.exit(1) 