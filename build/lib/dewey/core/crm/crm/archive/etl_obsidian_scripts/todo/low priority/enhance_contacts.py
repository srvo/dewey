import duckdb
from supabase import create_client
import pandas as pd
from typing import Dict, Set, List
import time
import os

# Supabase setup
supabase_url = "https://fjzxtsewrykbrfjzatti.supabase.co"
supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZqenh0c2V3cnlrYnJmanphdHRpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzE3NDE0ODUsImV4cCI6MjA0NzMxNzQ4NX0.faaMQ6bwUHdf5c0SjqUZ7Unr7JW8PtAb_-mG1V9Iang"

def extract_email_domain(email: str) -> str:
    """Extract domain from email address"""
    try:
        return email.split('@')[1].lower()
    except:
        return ""

def extract_email(email_string: str) -> str:
    """Extract email from format 'Name <email@domain.com>'"""
    if '<' in email_string:
        return email_string.split('<')[1].strip('>')
    return email_string.strip()

def analyze_contact_interactions(emails_data: List[dict], contact_email: str) -> dict:
    """Analyze email interactions with a contact to determine relationship strength"""
    sent_count = 0
    received_count = 0
    threads = set()
    first_interaction = None
    last_interaction = None
    
    for email in emails_data:
        is_interaction = False
        current_date = email['sent_date']
        
        # Check from address
        if extract_email(email['from_address']).lower() == contact_email:
            received_count += 1
            is_interaction = True
        
        # Check to addresses
        for to_addr in email['to_addresses']:
            if extract_email(to_addr).lower() == contact_email:
                sent_count += 1
                is_interaction = True
        
        if is_interaction:
            threads.add(email['thread_id'])
            if not first_interaction or current_date < first_interaction:
                first_interaction = current_date
            if not last_interaction or current_date > last_interaction:
                last_interaction = current_date
    
    return {
        'sent_count': sent_count,
        'received_count': received_count,
        'total_interactions': sent_count + received_count,
        'unique_threads': len(threads),
        'first_interaction': first_interaction,
        'last_interaction': last_interaction,
        'interaction_period_days': (last_interaction - first_interaction).days if first_interaction else 0
    }

def enhance_contacts():
    try:
        # Connect to Supabase
        supabase = create_client(supabase_url, supabase_key)
        print("Connected to Supabase")

        # Fetch existing data
        contacts = supabase.table('Contacts').select('*').execute()
        emails = supabase.table('Emails').select('*').execute()
        print(f"Fetched {len(contacts.data)} existing contacts")
        print(f"Fetched {len(emails.data)} emails")

        # Create set of known email addresses
        known_emails = {contact['Email'].lower() for contact in contacts.data if contact.get('Email')}
        print(f"Found {len(known_emails)} known email addresses")

        # Extract new unique contacts with detailed interaction analysis
        new_contacts: Dict[str, Dict] = {}
        for email in emails.data:
            # Process from_address
            if email['from_address']:
                email_addr = extract_email(email['from_address']).lower()
                if email_addr and email_addr not in known_emails and email_addr not in new_contacts:
                    name = email['from_address'].split('<')[0].strip()
                    name_parts = name.split(' ', 1)
                    first_name = name_parts[0] if name_parts else ''
                    last_name = name_parts[1] if len(name_parts) > 1 else ''
                    
                    interactions = analyze_contact_interactions(emails.data, email_addr)
                    
                    new_contacts[email_addr] = {
                        'Email': email_addr,
                        'first_name': first_name,
                        'last_name': last_name,
                        'full_name': name,
                        'from_header': email['from_address'],
                        'email_count': interactions['total_interactions'],
                        'last_contact_date': interactions['last_interaction'],
                        'contacted': True if interactions['total_interactions'] > 1 else False
                    }

        print(f"\nFound {len(new_contacts)} new unique contacts")

        # Identify potential clients based on interaction patterns
        potential_clients = []
        for email, data in new_contacts.items():
            interactions = analyze_contact_interactions(emails.data, email)
            
            if interactions['total_interactions'] >= 3:  # Significant interaction threshold
                potential_clients.append({
                    'email': email,
                    'name': data['full_name'],
                    'interactions': interactions['total_interactions'],
                    'unique_threads': interactions['unique_threads'],
                    'sent': interactions['sent_count'],
                    'received': interactions['received_count'],
                    'first_contact': interactions['first_interaction'],
                    'last_contact': interactions['last_interaction'],
                    'interaction_period_days': interactions['interaction_period_days']
                })

        # Sort by interaction count and recency
        potential_clients.sort(key=lambda x: (x['interactions'], x['last_contact']), reverse=True)

        print("\nPotential client relationships (3+ interactions):")
        for client in potential_clients[:20]:  # Show top 20
            print(f"\n{client['name']} ({client['email']}):")
            print(f"  - {client['interactions']} total interactions ({client['sent']} sent, {client['received']} received)")
            print(f"  - {client['unique_threads']} unique conversation threads")
            print(f"  - First contact: {client['first_contact'].strftime('%Y-%m-%d')}")
            print(f"  - Last contact: {client['last_contact'].strftime('%Y-%m-%d')}")
            print(f"  - Interaction period: {client['interaction_period_days']} days")

        # Save detailed analysis to CSV
        os.makedirs('/Users/srvo/lc/performance/output', exist_ok=True)
        potential_clients_df = pd.DataFrame(potential_clients)
        potential_clients_df.to_csv('/Users/srvo/lc/performance/output/potential_clients.csv', index=False)
        print(f"\nSaved detailed analysis of {len(potential_clients)} potential clients to CSV")

    except Exception as e:
        print(f"Error enhancing contacts: {str(e)}")

if __name__ == "__main__":
    enhance_contacts() 