import csv
import json
from pathlib import Path
from datetime import datetime
import re

def extract_name_from_email_header(header):
    """Extract name from email header format"""
    if not header:
        return '', ''
    
    # Try to match "Name Name (Optional)" <email> format
    match = re.match(r'"?([^"<]+)"?\s*<[^>]+>', header)
    if match:
        full_name = match.group(1).strip()
        # Split into first and last name
        parts = full_name.split(' ', 1)
        return parts[0], parts[1] if len(parts) > 1 else ''
    
    return '', ''

def parse_date(date_str):
    """Convert email date format to desired format"""
    try:
        # Parse various email date formats
        formats = [
            '%a, %d %b %Y %H:%M:%S %z',
            '%a, %d %b %Y %H:%M:%S %Z',
            '%d %b %Y %H:%M:%S %z',
            '%Y-%m-%d %H:%M:%S'
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.split('(')[0].strip(), fmt)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                continue
        
        return date_str
    except:
        return date_str

def process_email_data(input_file):
    """Process email data and create metadata dictionary"""
    email_metadata = {}
    
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            email = row['email_address']
            
            if email not in email_metadata:
                # Initialize new entry
                first_name, last_name = extract_name_from_email_header(row['sender'])
                email_metadata[email] = {
                    'Email': email,
                    'contacted': 'TRUE',
                    'last_contact_date': parse_date(row['date']),
                    'first_name': first_name,
                    'last_name': last_name,
                    'full_name': f"{first_name} {last_name}".strip(),
                    'company': '',  # Extract from email domain or other sources
                    'email_count': 1,
                    'from_header': row['sender'],
                    'Firstname': '',
                    'Lastname': '',
                    'Pronouns': ''
                }
            else:
                # Update existing entry
                email_metadata[email]['email_count'] += 1
                current_date = parse_date(row['date'])
                if current_date > email_metadata[email]['last_contact_date']:
                    email_metadata[email]['last_contact_date'] = current_date
    
    return email_metadata

def save_metadata(metadata, output_file):
    """Save metadata to CSV file"""
    fieldnames = [
        'Email', 'contacted', 'last_contact_date', 'first_name', 'last_name',
        'full_name', 'company', 'email_count', 'from_header', 'Firstname',
        'Lastname', 'Pronouns'
    ]
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for email in sorted(metadata.keys()):
            writer.writerow(metadata[email])

def main():
    # Set up file paths
    input_file = Path('output/email_analysis_20241114_150306.csv')
    output_file = Path('output/email_metadata.csv')
    
    print(f"Processing email data from {input_file}...")
    
    # Process the data
    metadata = process_email_data(input_file)
    
    # Save results
    save_metadata(metadata, output_file)
    
    print(f"\nProcessing complete!")
    print(f"Found {len(metadata)} unique email addresses")
    print(f"Results saved to {output_file}")
    
    # Print sample of results
    print("\nSample entries:")
    for email in list(metadata.keys())[:3]:
        print(f"\nEmail: {email}")
        print(f"Name: {metadata[email]['full_name']}")
        print(f"Last Contact: {metadata[email]['last_contact_date']}")
        print(f"Email Count: {metadata[email]['email_count']}")

if __name__ == "__main__":
    main() 