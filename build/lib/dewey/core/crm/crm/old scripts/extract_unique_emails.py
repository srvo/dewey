import json
import csv
import re
import sys
from pathlib import Path

def extract_emails_from_text(text):
    """Extract email addresses from text using regex"""
    if not text or not isinstance(text, str):
        return set()
        
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return set(re.findall(email_pattern, text))

def extract_emails_from_json(filepath):
    """Extract emails from JSON analysis files"""
    emails = set()
    
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        for entry in data:
            # Extract from metadata
            if 'metadata' in entry:
                metadata = entry['metadata']
                if 'sender' in metadata:
                    emails.update(extract_emails_from_text(metadata['sender']))
                    
            # Extract from analysis details
            if 'analysis' in entry and 'details' in entry['analysis']:
                details = entry['analysis']['details']
                if 'email' in details:
                    emails.update(extract_emails_from_text(str(details['email'])))
                    
            # Extract from content
            if 'analysis' in entry and 'content' in entry['analysis']:
                content = entry['analysis']['content']
                if 'raw_form_data' in content:
                    emails.update(extract_emails_from_text(str(content['raw_form_data'])))
                    
    except Exception as e:
        print(f"Error processing JSON file {filepath}: {str(e)}")
        
    return emails

def extract_emails_from_csv(filepath):
    """Extract emails from CSV files"""
    emails = set()
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Look for email-related column headers
            email_columns = [col for col in reader.fieldnames if 
                           col and any(term in col.lower() for term in 
                           ['email', 'e-mail', 'mail'])]
            
            # Process each row
            for row in reader:
                for col in email_columns:
                    if col in row and row[col]:
                        emails.update(extract_emails_from_text(row[col]))
                        
                # Also scan all fields for email addresses
                for value in row.values():
                    if value:
                        emails.update(extract_emails_from_text(str(value)))
                        
    except Exception as e:
        print(f"Error processing CSV file {filepath}: {str(e)}")
        
    return emails

def process_files(file_paths):
    """Process multiple files and return unique emails"""
    all_emails = set()
    
    for filepath in file_paths:
        print(f"Processing {filepath}...")
        
        if not Path(filepath).exists():
            print(f"File not found: {filepath}")
            continue
            
        if filepath.lower().endswith('.json'):
            emails = extract_emails_from_json(filepath)
        elif filepath.lower().endswith('.csv'):
            emails = extract_emails_from_csv(filepath)
        else:
            print(f"Unsupported file type: {filepath}")
            continue
            
        print(f"Found {len(emails)} email addresses in {filepath}")
        all_emails.update(emails)
        
    return all_emails

def main():
    # Input files
    files = [
        'email_analysis_20241114_045221.json',
        'email_analysis_20241114_045613.json',
        'email_analysis_20241114_045900.json',
        'scripts/csvs/virgin/☎️  Radical Planners Database ☎️ - Rad Planners Community List.csv',
        'scripts/csvs/virgin/Client_Contact Master - Free Money Podcast Email List.csv',
        'scripts/csvs/virgin/List for Sloane.xlsx - FOD V5.csv'
    ]
    
    # Output file
    output_file = 'unique_emails.txt'
    
    print("Starting email extraction process...")
    
    # Process all files
    unique_emails = process_files(files)
    
    # Sort emails alphabetically
    sorted_emails = sorted(unique_emails)
    
    # Save to file
    try:
        with open(output_file, 'w') as f:
            for email in sorted_emails:
                f.write(email + '\n')
        print(f"\nSuccessfully saved {len(sorted_emails)} unique email addresses to {output_file}")
    except Exception as e:
        print(f"Error saving output file: {str(e)}")
        
    # Print statistics
    print("\nExtraction Statistics:")
    print(f"Total unique email addresses: {len(sorted_emails)}")
    
    # Print domain statistics
    domains = {}
    for email in sorted_emails:
        domain = email.split('@')[-1].lower()
        domains[domain] = domains.get(domain, 0) + 1
        
    print("\nTop 10 email domains:")
    for domain, count in sorted(domains.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"{domain}: {count}")

if __name__ == "__main__":
    main() 