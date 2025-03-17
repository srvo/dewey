import pandas as pd
from supabase import create_client
import os
from pathlib import Path

# Supabase setup - using your hosted Supabase credentials
supabase_url = "https://fjzxtsewrykbrfjzatti.supabase.co"  # Make sure to use https://
supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZqenh0c2V3cnlrYnJmanphdHRpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzE3NDE0ODUsImV4cCI6MjA0NzMxNzQ4NX0.faaMQ6bwUHdf5c0SjqUZ7Unr7JW8PtAb_-mG1V9Iang"

try:
    supabase = create_client(supabase_url, supabase_key)
    print(f"Successfully connected to Supabase")
except Exception as e:
    print(f"Error connecting to Supabase: {str(e)}")
    exit(1)

# Base data directory
data_dir = Path("/Users/srvo/lc/performance/data")

def upload_data():
    """Upload data from CSV files to Supabase"""
    try:
        # Test connection first
        test = supabase.table('clients').select("count").execute()
        print("Database connection verified")
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        return

    # Load clients
    clients_file = data_dir / "clients.csv"
    if clients_file.exists():
        df_clients = pd.read_csv(clients_file)
        clients_data = df_clients.where(pd.notnull(df_clients), None).to_dict('records')
        if clients_data:
            result = supabase.table('clients').insert(clients_data).execute()
            print(f"Uploaded {len(clients_data)} clients")

def verify_data():
    """Verify the uploaded data"""
    try:
        clients = supabase.table('clients').select("*").execute()
        print(f"\nData verification:")
        print(f"Clients: {len(clients.data)}")
    except Exception as e:
        print(f"Error verifying data: {str(e)}")

def main():
    print("\nUploading data...")
    upload_data()
    
    print("\nVerifying data...")
    verify_data()

if __name__ == "__main__":
    main()