from pathlib import Path
import pandas as pd
from supabase import create_client

# Supabase setup
supabase_url = "https://fjzxtsewrykbrfjzatti.supabase.co"
supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZqenh0c2V3cnlrYnJmanphdHRpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzE3NDE0ODUsImV4cCI6MjA0NzMxNzQ4NX0.faaMQ6bwUHdf5c0SjqUZ7Unr7JW8PtAb_-mG1V9Iang"

def update_clients():
    try:
        # Initialize Supabase client
        supabase = create_client(supabase_url, supabase_key)
        print("Connected to Supabase")

        # Read households data
        households_file = Path("/Users/srvo/lc/data/portfolio/archive/20241130/Households - 20241130.csv")
        if not households_file.exists():
            raise FileNotFoundError(f"Households file not found at {households_file}")

        households_df = pd.read_csv(households_file)
        print(f"Found {len(households_df)} households")

        # Process each household
        for _, row in households_df.iterrows():
            # Use the full household name
            household_name = row['Name'].strip()
            
            # Split into first/last for database structure but preserve original name
            name_parts = household_name.split(',', 1)
            if len(name_parts) == 2:
                last_name = name_parts[0].strip()
                first_name = name_parts[1].strip()
            else:
                # Handle single name case
                first_name = household_name
                last_name = ""

            # Prepare client data
            client = {
                "first_name": first_name,
                "last_name": last_name,
                "household_name": household_name,  # Store the original household name
                "status": "active",
                "balance": float(row['Balance'].replace('$', '').replace(',', '')),
                "accounts": int(row['# of Accounts']),
                "cash_allocation": float(row['Cash'].rstrip('%')) / 100
            }

            # Check if household exists
            existing = supabase.table('clients').select("*").eq('household_name', household_name).execute()
            
            if existing.data:
                # Update existing household
                client_id = existing.data[0]['id']
                result = supabase.table('clients').update(client).eq('id', client_id).execute()
                print(f"Updated household: {household_name}")
            else:
                # Create new household
                result = supabase.table('clients').insert(client).execute()
                print(f"Created household: {household_name}")

        print("\nClient update complete!")

    except Exception as e:
        print(f"Error updating clients: {str(e)}")

if __name__ == "__main__":
    update_clients() 