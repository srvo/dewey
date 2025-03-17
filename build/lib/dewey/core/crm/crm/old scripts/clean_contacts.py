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
    return ' '.join(name.lower().split())

def clean_contacts():
    try:
        client = SupabaseClient().get_client()
        print("Connected to Supabase")

        # Fetch all contacts
        contacts = client.table('Contacts').select('*').execute()
        print(f"\nFetched {len(contacts.data)} contacts")

        # Find Sloane's records
        sloane_contacts = []
        other_contacts = []
        
        for contact in contacts.data:
            if contact.get('full_name'):
                name = normalize_name(contact['full_name'])
                if 'sloane' in name and 'ortel' in name:
                    sloane_contacts.append(contact)
                else:
                    other_contacts.append(contact)

        print(f"\nFound {len(sloane_contacts)} duplicate Sloane records:")
        for contact in sloane_contacts:
            print(f"ID: {contact['Entity ID']}")
            print(f"Name: {contact['full_name']}")
            print(f"Email: {contact.get('Email', 'No email')}")
            print("---")

        # Create a CSV for review
        df = pd.DataFrame(sloane_contacts)
        review_path = '/Users/srvo/lc/performance/output/duplicate_contacts.csv'
        df.to_csv(review_path, index=False)
        print(f"\nSaved contact details to {review_path} for review")

        # Ask for confirmation
        correct_id = input("\nEnter the ID of the contact record to keep: ")
        correct_email = input("Enter your correct email address: ")

        if not correct_id or not correct_email:
            print("No changes made")
            return

        # Update the correct record
        try:
            client.table('Contacts').update({
                'Email': correct_email,
                'is_advisor': True
            }).eq('Entity ID', correct_id).execute()
            print(f"\nUpdated contact {correct_id} with email {correct_email}")

            # Delete other Sloane records
            for contact in sloane_contacts:
                if contact['Entity ID'] != correct_id:
                    client.table('Contacts').delete().eq('Entity ID', contact['Entity ID']).execute()
                    print(f"Deleted duplicate contact {contact['Entity ID']}")

            print("\nContact cleanup complete!")

        except Exception as e:
            print(f"Error updating contacts: {str(e)}")

    except Exception as e:
        print(f"Error: {str(e)}")
        print(f"Error type: {type(e)}")

if __name__ == "__main__":
    clean_contacts() 