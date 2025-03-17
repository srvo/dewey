import csv
import os
from csv_reader import read_csv_file

def save_contacts(contacts, output_file):
    fieldnames = ['first_name', 'last_name', 'email', 'phone', 'full_name', 
                 'website', 'address_1', 'address_2', 'city', 'state', 'zip', 
                 'country', 'notes', 'current_client', 'investment_professional', 
                 'last_contact']
    
    print(f"\nDEBUG: About to write {len(contacts)} contacts to {output_file}")
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for contact in contacts:
            writer.writerow(contact)

def save_relationships(relationships, output_file):
    fieldnames = ['contact_email', 'referrer_name', 'relationship_type']
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for relationship in relationships:
            writer.writerow(relationship)

def merge_contacts(existing, new):
    """Merge two contact records, preserving the most complete information."""
    merged = existing.copy()
    
    # For each field in the new contact
    for key, new_value in new.items():
        if not new_value:
            continue
            
        # If we don't have this info yet, use it
        if not merged[key]:
            merged[key] = new_value
            continue
            
        # Special handling for notes - concatenate with separator
        if key == 'notes' and new_value != merged[key]:
            merged[key] = f"{merged[key]} | {new_value}".strip(' |')
            continue
            
        # For other fields, prefer longer/more complete values
        if len(str(new_value)) > len(str(merged[key])):
            merged[key] = new_value
    
    return merged

def clean_phone(phone):
    """Standardize phone number format."""
    if not phone:
        return ''
    # Remove all non-numeric characters
    digits = ''.join(c for c in phone if c.isdigit())
    if len(digits) >= 10:
        return f"+{digits}"
    return phone

def deduplicate_contacts(contacts):
    """Deduplicate contacts by email while preserving all information."""
    unique_contacts = {}
    
    for contact in contacts:
        email = contact['email'].lower().strip()  # Case-insensitive matching
        
        # Clean up phone numbers
        contact['phone'] = clean_phone(contact['phone'])
        
        # Clean up names
        for name_field in ['first_name', 'last_name']:
            if contact[name_field]:
                contact[name_field] = contact[name_field].strip().title()
        
        if email in unique_contacts:
            # Merge with existing contact
            unique_contacts[email] = merge_contacts(unique_contacts[email], contact)
        else:
            unique_contacts[email] = contact
    
    return list(unique_contacts.values())

def main():
    input_dir = 'scripts/csvs'
    contacts_file = 'standardized_contacts.csv'
    relationships_file = 'contact_relationships.csv'
    
    all_contacts = []
    all_relationships = []

    for filename in os.listdir(input_dir):
        if filename.endswith('.csv'):
            filepath = os.path.join(input_dir, filename)
            print(f"\nProcessing {filename}...")
            contacts, relationships = read_csv_file(filepath)
            
            print(f"Found {len(contacts)} contacts")
            if len(contacts) > 0:
                sample = contacts[0]
                filled_fields = [k for k,v in sample.items() if v]
                print(f"Sample fields present: {', '.join(filled_fields)}")
            
            all_contacts.extend(contacts)
            all_relationships.extend(relationships)

    # Deduplicate contacts
    original_count = len(all_contacts)
    all_contacts = deduplicate_contacts(all_contacts)
    
    # Sort contacts by email for consistency
    all_contacts.sort(key=lambda x: x['email'])
    
    print(f"\nReduced {original_count} contacts to {len(all_contacts)} unique contacts")
    
    # Print some stats
    filled_counts = {field: sum(1 for c in all_contacts if c[field]) 
                    for field in all_contacts[0].keys()}
    print(f"Filled fields: {', '.join(f'{field}: {count}' for field, count in filled_counts.items())}")

    print(f"Total relationships: {len(all_relationships)}")

    save_contacts(all_contacts, contacts_file)
    save_relationships(all_relationships, relationships_file)

if __name__ == '__main__':
    main()