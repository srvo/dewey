from supabase_client import SupabaseClient

def test_tables():
    try:
        # Get client with service role access
        client = SupabaseClient().get_client()
        print("Connected to Supabase")

        # Test each table
        print("\nTesting Contacts table:")
        contacts = client.table('Contacts').select('*').limit(5).execute()
        print(f"- Found {len(contacts.data)} rows")
        if contacts.data:
            print(f"- Sample columns: {list(contacts.data[0].keys())}")

        print("\nTesting Clients table:")
        clients = client.table('Clients').select('*').limit(5).execute()
        print(f"- Found {len(clients.data)} rows")
        if clients.data:
            print(f"- Sample columns: {list(clients.data[0].keys())}")

        print("\nTesting Emails table:")
        emails = client.table('Emails').select('*').limit(5).execute()
        print(f"- Found {len(emails.data)} rows")
        if emails.data:
            print(f"- Sample columns: {list(emails.data[0].keys())}")

    except Exception as e:
        print(f"Error: {str(e)}")
        print(f"Error type: {type(e)}")

if __name__ == "__main__":
    test_tables() 