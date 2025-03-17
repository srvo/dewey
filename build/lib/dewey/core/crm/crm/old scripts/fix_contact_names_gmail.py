from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from supabase_client import SupabaseClient
from typing import Dict, List, Set
import pandas as pd
import pickle
import os

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    """Get authenticated Gmail service"""
    creds = None
    token_path = '/Users/srvo/lc/data/token.pickle'
    creds_path = '/Users/srvo/lc/data/credentials.json'

    # Load existing token
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    # Refresh or get new token
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save token
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    return build('gmail', 'v1', credentials=creds)

def get_name_from_gmail(email: str, service) -> str:
    """Search Gmail for emails from this address to find the sender name"""
    try:
        # Search for recent emails from this address
        query = f'from:{email}'
        results = service.users().messages().list(userId='me', q=query, maxResults=1).execute()
        messages = results.get('messages', [])

        if messages:
            # Get the first message's headers
            msg = service.users().messages().get(userId='me', id=messages[0]['id'], format='metadata',
                                               metadataHeaders=['From']).execute()
            
            # Extract sender info
            headers = msg['payload']['headers']
            from_header = next((h['value'] for h in headers if h['name'] == 'From'), None)
            
            if from_header:
                # Parse "Name <email@example.com>" format
                if '<' in from_header:
                    name = from_header.split('<')[0].strip()
                    if name and name != email:
                        return name
        
        return None

    except Exception as e:
        print(f"Error searching Gmail for {email}: {str(e)}")
        return None

def fix_contact_names():
    try:
        # Connect to Supabase
        client = SupabaseClient().get_client()
        print("Connected to Supabase")

        # Get Gmail service
        print("Authenticating with Gmail...")
        service = get_gmail_service()
        print("Gmail authentication successful")

        # Fetch contacts
        contacts = client.table('Contacts').select('*').execute()
        print(f"Fetched {len(contacts.data)} contacts")

        # Find contacts incorrectly marked as Sloane
        incorrect_contacts = []
        for contact in contacts.data:
            if contact.get('full_name') and contact.get('Email'):
                name = contact['full_name'].lower()
                if 'sloane' in name and 'ortel' in name:
                    print(f"\nChecking Gmail for {contact['Email']}...")
                    real_name = get_name_from_gmail(contact['Email'], service)
                    
                    incorrect_contacts.append({
                        'id': contact['Entity ID'],
                        'email': contact['Email'],
                        'current_name': contact['full_name'],
                        'suggested_name': real_name if real_name else "Unknown"
                    })

        # Save results
        if incorrect_contacts:
            df = pd.DataFrame(incorrect_contacts)
            output_path = '/Users/srvo/lc/performance/output/contacts_to_fix_gmail.csv'
            df.to_csv(output_path, index=False)
            print(f"\nSaved {len(incorrect_contacts)} contacts to {output_path}")
            
            print("\nSample of contacts to fix:")
            for contact in incorrect_contacts[:10]:
                print(f"\nEmail: {contact['email']}")
                print(f"Current name: {contact['current_name']}")
                print(f"Suggested name: {contact['suggested_name']}")

    except Exception as e:
        print(f"Error: {str(e)}")
        print(f"Error type: {type(e)}")

if __name__ == "__main__":
    fix_contact_names() 