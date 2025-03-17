from supabase import create_client

# Supabase setup
supabase_url = "https://fjzxtsewrykbrfjzatti.supabase.co"
supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZqenh0c2V3cnlrYnJmanphdHRpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzE3NDE0ODUsImV4cCI6MjA0NzMxNzQ4NX0.faaMQ6bwUHdf5c0SjqUZ7Unr7JW8PtAb_-mG1V9Iang"

def check_permissions():
    try:
        supabase = create_client(supabase_url, supabase_key)
        print("Connected to Supabase")

        # Try to get table info
        print("\nChecking 'Contacts' table:")
        contacts = supabase.table('Contacts').select('count').execute()
        print(f"Count query result: {contacts.data}")

        print("\nTrying to insert a test contact:")
        test_contact = {
            "Email": "test@example.com",
            "contacted": False,
            "first_name": "Test",
            "last_name": "User"
        }
        try:
            result = supabase.table('Contacts').insert(test_contact).execute()
            print("Insert successful:", result.data)
        except Exception as e:
            print(f"Insert failed: {str(e)}")

        print("\nChecking 'Clients' table:")
        clients = supabase.table('Clients').select('count').execute()
        print(f"Count query result: {clients.data}")

    except Exception as e:
        print(f"Error: {str(e)}")
        print(f"Error type: {type(e)}")
        print(f"Error details: {getattr(e, 'details', 'No details available')}")

if __name__ == "__main__":
    check_permissions() 