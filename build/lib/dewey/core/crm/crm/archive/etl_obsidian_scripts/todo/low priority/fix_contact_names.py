from supabase_client import SupabaseClient
from typing import Dict, List, Set
import pandas as pd
import re

def get_name_from_emails(email: str, emails_data: List[dict]) -> str:
    """Try to find the real name associated with this email from email records"""
    matching_emails = [e for e in emails_data if 
                      e.get('from_address') == email or 
                      (isinstance(e.get('to_addresses'), str) and email in e.get('to_addresses'))]
    
    if matching_emails:
        # Look for from_name or to_name fields
        for email_record in matching_emails:
            if email_record.get('from_address') == email and email_record.get('from_name'):
                return email_record['from_name']
            # Check to_name if it exists and matches
            if email_record.get('to_name') and email in email_record.get('to_addresses', ''):
                return email_record['to_name']
    
    return None

def fix_contact_names():
    try:
        client = SupabaseClient().get_client()
        print("Connected to Supabase")

        # Fetch all data
        contacts = client.table('Contacts').select('*').execute()
        emails = client.table('Emails').select('*').execute()
        
        print(f"Fetched {len(contacts.data)} contacts")
        print(f"Fetched {len(emails.data)} emails")

        # Find contacts incorrectly marked as Sloane
        incorrect_contacts = []
        for contact in contacts.data:
            if contact.get('full_name') and contact.get('Email'):
                name = contact['full_name'].lower()
                if 'sloane' in name and 'ortel' in name:
                    real_name = get_name_from_emails(contact['Email'], emails.data)
                    incorrect_contacts.append({
                        'id': contact['Entity ID'],
                        'email': contact['Email'],
                        'current_name': contact['full_name'],
                        'suggested_name': real_name if real_name else "Unknown",
                        'email_count': len([e for e in emails.data if 
                                         e.get('from_address') == contact['Email'] or 
                                         (isinstance(e.get('to_addresses'), str) and 
                                          contact['Email'] in e.get('to_addresses'))])
                    })

        # Save to CSV for review
        if incorrect_contacts:
            df = pd.DataFrame(incorrect_contacts)
            output_path = '/Users/srvo/lc/performance/output/contacts_to_fix.csv'
            df.to_csv(output_path, index=False)
            print(f"\nSaved {len(incorrect_contacts)} contacts to {output_path}")
            
            print("\nSample of contacts to fix:")
            for contact in incorrect_contacts[:10]:
                print(f"\nEmail: {contact['email']}")
                print(f"Current name: {contact['current_name']}")
                print(f"Suggested name: {contact['suggested_name']}")
                print(f"Found in {contact['email_count']} emails")

    except Exception as e:
        print(f"Error: {str(e)}")
        print(f"Error type: {type(e)}")

if __name__ == "__main__":
    fix_contact_names() 