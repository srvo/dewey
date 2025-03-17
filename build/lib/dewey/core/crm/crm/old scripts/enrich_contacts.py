import csv
import os
from pathlib import Path

def load_existing_contacts(contacts_file):
    """Load our existing contacts CSV as a dictionary keyed by email"""
    print(f"Attempting to load contacts from: {contacts_file}")
    if not os.path.exists(contacts_file):
        print(f"ERROR: File not found: {contacts_file}")
        return {}
        
    contacts = {}
    try:
        with open(contacts_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row['email'].lower().strip()
                contacts[email] = row
        print(f"Successfully loaded {len(contacts)} contacts")
    except Exception as e:
        print(f"ERROR loading contacts: {str(e)}")
        return {}
        
    return contacts

def merge_contact_data(existing, new):
    """Merge new contact data into existing record, preserving all information"""
    merged = existing.copy()
    
    for key, new_value in new.items():
        new_value = str(new_value).strip()
        if not new_value:
            continue
            
        existing_value = merged.get(key, '').strip()
        
        # If we don't have this info yet, use the new value
        if not existing_value:
            merged[key] = new_value
            continue
            
        # For notes, concatenate unique information
        if key == 'notes' and new_value != existing_value:
            notes = set([n.strip() for n in existing_value.split('|')] + [new_value])
            merged[key] = ' | '.join(filter(None, notes))
            continue
            
        # For other fields, prefer longer/more complete values
        if len(new_value) > len(existing_value):
            merged[key] = new_value
            
    return merged

def clean_phone(phone):
    """Standardize phone number format"""
    if not phone:
        return ''
    digits = ''.join(c for c in phone if c.isdigit())
    if len(digits) >= 10:
        return f"+{digits}"
    return phone

def extract_contact_data(row):
    """Extract contact data from a row using various possible field names"""
    contact = {
        'first_name': '',
        'last_name': '',
        'email': '',
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
    
    # Try various email field patterns
    email = (
        row.get('Email Address', '') or 
        row.get('User Email', '') or
        row.get('Email', '') or
        row.get('Subscriber', '') or
        row.get('Your Information - Email Address', '')
    ).strip().lower()
    
    if not email:
        return None
        
    contact['email'] = email
    
    # Names
    contact['first_name'] = (
        row.get('First Name', '') or
        row.get('Name - First Name', '') or
        row.get('Your Information - Name', '').split()[0] if row.get('Your Information - Name', '') else ''
    ).strip()
    
    contact['last_name'] = (
        row.get('Last Name', '') or
        row.get('Name - Last Name', '') or
        ' '.join(row.get('Your Information - Name', '').split()[1:]) if row.get('Your Information - Name', '') else ''
    ).strip()
    
    # Phone
    contact['phone'] = clean_phone(
        row.get('Phone Number', '') or
        row.get('Primary Phone', '') or
        row.get('Your Information - Phone Number', '') or
        row.get('Business Phone', '')
    )
    
    # Address
    contact['address_1'] = (
        row.get('Street Address', '') or
        row.get('Your Information - Address - Street Address', '') or
        row.get('Primary Street', '')
    ).strip()
    
    contact['city'] = (
        row.get('City', '') or
        row.get('Your Information - Address - City', '') or
        row.get('Primary City', '')
    ).strip()
    
    contact['state'] = (
        row.get('State', '') or
        row.get('Your Information - Address - State/Province', '') or
        row.get('Primary State', '')
    ).strip()
    
    # Notes and other fields
    notes = []
    if row.get('Notes'): notes.append(row['Notes'])
    if row.get('Contact Description'): notes.append(row['Contact Description'])
    if row.get('Additional Information'): notes.append(row['Additional Information'])
    contact['notes'] = ' | '.join(filter(None, notes))
    
    return contact

def main():
    # Update file paths
    base_dir = Path('/Users/srvo/Data')
    contacts_file = base_dir / 'standardized_contacts.csv'
    csv_dir = base_dir / 'scripts' / 'csvs'
    output_file = base_dir / 'enriched_contacts.csv'
    
    print(f"\nStarting contact enrichment process...")
    print(f"Base directory: {base_dir}")
    print(f"Looking for contacts file: {contacts_file}")
    print(f"Looking for CSV directory: {csv_dir}")
    print(f"Will save output to: {output_file}")
    
    # Verify directories exist
    if not csv_dir.exists():
        print(f"ERROR: CSV directory not found: {csv_dir}")
        return
        
    # Load existing contacts
    contacts = load_existing_contacts(contacts_file)
    if not contacts:
        print("No contacts loaded, exiting.")
        return
    
    # Process all CSVs in the directory
    csv_files = list(csv_dir.glob('*.csv'))
    print(f"\nFound {len(csv_files)} CSV files to process")
    
    for csv_file in csv_files:
        print(f"\nProcessing {csv_file.name}")
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows_processed = 0
                contacts_enriched = 0
                
                for row in reader:
                    rows_processed += 1
                    contact_data = extract_contact_data(row)
                    
                    if contact_data and contact_data['email'] in contacts:
                        contacts[contact_data['email']] = merge_contact_data(
                            contacts[contact_data['email']], 
                            contact_data
                        )
                        contacts_enriched += 1
                        
                print(f"Processed {rows_processed} rows")
                print(f"Enriched {contacts_enriched} contacts")
        except Exception as e:
            print(f"ERROR processing {csv_file.name}: {str(e)}")
    
    if not contacts:
        print("\nNo contacts to save, exiting.")
        return
        
    # Save enriched contacts
    try:
        fieldnames = list(next(iter(contacts.values())).keys())
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for contact in sorted(contacts.values(), key=lambda x: x['email']):
                writer.writerow(contact)
                
        print(f"\nSaved enriched contacts to {output_file}")
        
        # Print some stats
        filled_counts = {
            field: sum(1 for c in contacts.values() if c[field]) 
            for field in fieldnames
        }
        print("\nField completion stats:")
        for field, count in filled_counts.items():
            print(f"{field}: {count} contacts ({count/len(contacts)*100:.1f}%)")
            
    except Exception as e:
        print(f"ERROR saving output file: {str(e)}")

if __name__ == '__main__':
    main()
