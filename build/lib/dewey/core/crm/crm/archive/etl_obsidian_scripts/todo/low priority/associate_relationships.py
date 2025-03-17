import duckdb
from supabase import create_client
from typing import Dict, List, Set
import pandas as pd
import time

# Supabase setup (using same credentials as upload_emails.py)
supabase_url = "https://fjzxtsewrykbrfjzatti.supabase.co"
supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZqenh0c2V3cnlrYnJmanphdHRpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzE3NDE0ODUsImV4cCI6MjA0NzMxNzQ4NX0.faaMQ6bwUHdf5c0SjqUZ7Unr7JW8PtAb_-mG1V9Iang"

def extract_email(email_string: str) -> str:
    """Extract email from format 'Name <email@domain.com>'"""
    if '<' in email_string:
        return email_string.split('<')[1].strip('>')
    return email_string.strip()

def associate_relationships():
    try:
        # Connect to services
        supabase = create_client(supabase_url, supabase_key)
        print("Connected to Supabase")

        # 1. Fetch all clients and contacts from Supabase
        clients = supabase.table('Clients').select('*').execute()
        contacts = supabase.table('Contacts').select('*').execute()
        emails = supabase.table('Emails').select('*').execute()
        
        print(f"Fetched {len(clients.data)} clients")
        print(f"Fetched {len(contacts.data)} contacts")
        print(f"Fetched {len(emails.data)} emails")

        # Create email address to contact ID mapping
        email_to_contact: Dict[str, str] = {}
        for contact in contacts.data:
            if contact.get('email'):
                email_to_contact[contact['email'].lower()] = contact['id']
        print(f"Created mapping for {len(email_to_contact)} contact emails")

        # 2. Associate contacts with clients
        total_client_associations = 0
        for client in clients.data:
            # Find contacts that match client domain
            client_domain = client['domain']
            if not client_domain:
                print(f"Skipping client {client['name']} - no domain specified")
                continue

            matching_contacts = []
            for contact in contacts.data:
                if contact.get('email', '').lower().endswith(client_domain.lower()):
                    matching_contacts.append({
                        'contact_id': contact['id'],
                        'client_id': client['id']
                    })

            # Update contact-client relationships in batches
            if matching_contacts:
                for i in range(0, len(matching_contacts), 50):
                    batch = matching_contacts[i:i+50]
                    supabase.table('ContactClientRelationships').upsert(batch).execute()
                total_client_associations += len(matching_contacts)
                print(f"Associated {len(matching_contacts)} contacts with client {client['name']} ({client_domain})")

        print(f"\nTotal client-contact associations: {total_client_associations}")

        # 3. Associate emails with contacts
        total_email_associations = 0
        for i, email in enumerate(emails.data):
            updates = []
            
            # Check from_address
            from_email = extract_email(email['from_address']).lower()
            if from_email in email_to_contact:
                updates.append({
                    'id': email['id'],
                    'contact_id': email_to_contact[from_email],
                    'direction': 'from'
                })

            # Check to_addresses
            for to_address in email['to_addresses']:
                to_email = extract_email(to_address).lower()
                if to_email in email_to_contact:
                    updates.append({
                        'id': email['id'],
                        'contact_id': email_to_contact[to_email],
                        'direction': 'to'
                    })

            # Update email-contact relationships in batches
            if updates:
                for update in updates:
                    supabase.table('EmailContactRelationships').upsert(update).execute()
                total_email_associations += len(updates)
            
            # Progress update every 100 emails
            if (i + 1) % 100 == 0:
                print(f"Processed {i + 1}/{len(emails.data)} emails...")

        print(f"\nTotal email-contact associations: {total_email_associations}")
        print("\nRelationship association complete!")

    except Exception as e:
        print(f"Error associating relationships: {str(e)}")

if __name__ == "__main__":
    associate_relationships() 