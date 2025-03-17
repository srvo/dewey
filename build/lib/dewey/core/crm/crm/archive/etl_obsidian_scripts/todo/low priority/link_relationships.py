from supabase_client import SupabaseClient
from typing import Dict, List, Set
import pandas as pd
import re

def normalize_name(name: str) -> str:
    """Remove pronouns, titles, and normalize whitespace"""
    if not name:
        return ''
    # Remove content in parentheses
    name = re.sub(r'\([^)]*\)', '', name)
    # Remove titles and suffixes
    name = re.sub(r'\b(Mr\.|Mrs\.|Ms\.|Dr\.|Jr\.|Sr\.|CFA|FRM|PhD|MD|DDS|Esq\.)\b', '', name)
    # Convert to lowercase and normalize whitespace
    return ' '.join(name.lower().split())

def get_advisor_emails(contacts: List[dict]) -> Set[str]:
    """Get all email addresses associated with the advisor (Sloane Ortel)"""
    advisor_emails = set()
    print("\nLooking for advisor (Sloane Ortel) contact records...")
    
    for contact in contacts:
        if contact.get('full_name') and contact.get('Email'):
            name = normalize_name(contact['full_name'])
            # Much stricter matching for advisor
            if 'sloane' in name and 'ortel' in name:
                print(f"Found advisor contact: {contact['full_name']} <{contact['Email']}>")
                advisor_emails.add(contact['Email'].lower())
    
    if not advisor_emails:
        print("Warning: Could not find any email addresses for Sloane Ortel")
    else:
        print(f"\nFound {len(advisor_emails)} advisor email addresses:")
        for email in advisor_emails:
            print(f"- {email}")
            
    return advisor_emails

def safe_string(value) -> str:
    """Safely convert value to lowercase string"""
    if isinstance(value, list):
        return ' '.join(str(x).lower() for x in value)
    return str(value).lower() if value else ''

def link_relationships():
    try:
        client = SupabaseClient().get_client()
        print("Connected to Supabase")

        # Fetch all data
        contacts = client.table('Contacts').select('*').execute()
        clients = client.table('Clients').select('*').execute()
        emails = client.table('Emails').select('*').execute()
        
        print(f"Fetched {len(contacts.data)} contacts")
        print(f"Fetched {len(clients.data)} clients")
        print(f"Fetched {len(emails.data)} emails")

        # Get advisor emails
        advisor_emails = get_advisor_emails(contacts.data)
        print(f"\nFound {len(advisor_emails)} advisor email addresses:")
        for email in advisor_emails:
            print(f"- {email}")

        # Create client lookup by email
        client_emails: Dict[str, dict] = {}
        contact_client_map: Dict[str, dict] = {}
        
        # First map contacts to clients
        for client in clients.data:
            if not client.get('household_name'):
                continue
                
            # Find all contacts associated with this client
            for contact in contacts.data:
                if not contact.get('Email') or not contact.get('full_name'):
                    continue
                    
                contact_name = normalize_name(contact['full_name'])
                client_name = normalize_name(client['household_name'])
                
                # Skip if this is the advisor
                if 'sloane' in contact_name and 'ortel' in contact_name:
                    continue
                
                # If contact name appears in client household name
                if any(part in client_name for part in contact_name.split()):
                    contact_email = contact['Email'].lower()
                    client_emails[contact_email] = {
                        'client_id': client['id'],
                        'client_name': client['household_name'],
                        'contact_id': contact['Entity ID'],
                        'contact_name': contact['full_name']
                    }

        # Process emails
        email_updates = []
        print("\nAnalyzing emails...")
        
        for email in emails.data:
            # Skip if already has client_id
            if email.get('client_id'):
                continue
                
            from_email = safe_string(email.get('from_address'))
            to_addresses = safe_string(email.get('to_addresses'))
            
            # Case 1: Email from advisor to client
            if any(advisor_email in from_email for advisor_email in advisor_emails):
                for client_email in client_emails:
                    if client_email in to_addresses:
                        client_info = client_emails[client_email]
                        email_updates.append({
                            'id': email['id'],
                            'client_id': client_info['client_id'],
                            'direction': 'outbound',
                            'client_name': client_info['client_name'],
                            'client_email': client_email,
                            'from_address': from_email,
                            'to_addresses': to_addresses
                        })
                        print(f"Found outbound email to client {client_info['client_name']}")
                        break
                        
            # Case 2: Email from client to advisor
            elif any(advisor_email in to_addresses for advisor_email in advisor_emails):
                if from_email in client_emails:
                    client_info = client_emails[from_email]
                    email_updates.append({
                        'id': email['id'],
                        'client_id': client_info['client_id'],
                        'direction': 'inbound',
                        'client_name': client_info['client_name'],
                        'client_email': from_email,
                        'from_address': from_email,
                        'to_addresses': to_addresses
                    })
                    print(f"Found inbound email from client {client_info['client_name']}")

        if email_updates:
            print(f"\nFound {len(email_updates)} emails to update")
            
            # Save to CSV
            df = pd.DataFrame(email_updates)
            output_path = '/Users/srvo/lc/performance/output/email_client_updates.csv'
            df.to_csv(output_path, index=False)
            print(f"\nSaved {len(email_updates)} updates to {output_path}")

            # Update database
            print("\nUpdating database...")
            supabase = SupabaseClient().get_client()
            for update in email_updates:
                try:
                    supabase.table('Emails').update(
                        {"client_id": update['client_id']}
                    ).eq('id', update['id']).execute()
                except Exception as e:
                    print(f"Error updating email {update['id']}: {str(e)}")

            print("Updates complete!")

    except Exception as e:
        print(f"Error: {str(e)}")
        print(f"Error type: {type(e)}")

if __name__ == "__main__":
    link_relationships() 