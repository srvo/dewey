import csv
from field_mappings import CONTACT_FIELDS

def read_csv_file(filepath):
    contacts = []
    relationships = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            # Get email (primary key)
            email = (
                row.get('Email Address', '') or 
                row.get('User Email|hidden-3', '') or 
                row.get('Your Information - Email Address', '') or
                row.get('Email', '') or
                row.get('Subscriber', '')
            ).strip()
            
            if email:
                # Create contact record
                contact = {
                    'first_name': '',
                    'last_name': '',
                    'email': email,
                    'phone': '',
                    'full_name': '',
                    'website': '',
                    'address_1': '',
                    'address_2': '',
                    'city': '',
                    'state': '',
                    'zip': '',
                    'country': '',
                    'notes': '',
                    'current_client': '',
                    'investment_professional': '',
                    'last_contact': ''
                }
                
                # Fill in contact details...
                # [previous contact field mapping code here]
                
                # Check notes field for relationships
                notes = row.get('Notes', '')
                if 'referred' in notes.lower():
                    # Extract referrer name
                    relationship = {
                        'contact_email': email,
                        'referrer_name': notes.split('referred')[0].strip(),
                        'relationship_type': 'referral'
                    }
                    relationships.append(relationship)
                
                contacts.append(contact)
    
    return contacts, relationships