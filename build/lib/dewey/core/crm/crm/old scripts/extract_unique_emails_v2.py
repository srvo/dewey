import json
import csv
import re
import sys
from pathlib import Path
from datetime import datetime

def load_existing_emails(filepath):
    """Load existing emails from reference file"""
    try:
        with open(filepath, 'r') as f:
            return {line.strip() for line in f if line.strip()}
    except FileNotFoundError:
        print(f"Reference file not found: {filepath}")
        return set()
    except Exception as e:
        print(f"Error loading reference file: {str(e)}")
        return set()

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

def process_files(file_paths, existing_emails):
    """Process multiple files and compare with existing emails"""
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
    
    # Compare with existing emails
    new_emails = all_emails - existing_emails
    existing_matches = all_emails & existing_emails
    
    return all_emails, new_emails, existing_matches

def save_results(all_emails, new_emails, existing_matches, output_dir):
    """Save results to multiple files"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create output directory if it doesn't exist
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Update the main unique_emails.txt file
    with open(output_dir / 'unique_emails.txt', 'w') as f:
        for email in sorted(all_emails):
            f.write(email + '\n')
            
    # Save new emails
    if new_emails:
        with open(output_dir / f'new_emails_{timestamp}.txt', 'w') as f:
            for email in sorted(new_emails):
                f.write(email + '\n')
                
    # Save comparison report
    with open(output_dir / f'email_comparison_report_{timestamp}.txt', 'w') as f:
        f.write("Email Comparison Report\n")
        f.write("======================\n\n")
        f.write(f"Total unique emails found: {len(all_emails)}\n")
        f.write(f"New emails found: {len(new_emails)}\n")
        f.write(f"Existing emails matched: {len(existing_matches)}\n\n")
        
        if new_emails:
            f.write("New Emails:\n")
            f.write("-----------\n")
            for email in sorted(new_emails):
                f.write(email + '\n')

def main():
    # Project paths
    project_root = Path(__file__).parent.parent
    data_dir = project_root / 'data'
    output_dir = project_root / 'output'
    
    # Reference file
    reference_file = project_root / 'unique_emails.txt'
    
    # Input files to process
    files = [
        data_dir / 'email_analysis_20241114_045221.json',
        data_dir / 'email_analysis_20241114_045613.json',
        data_dir / 'email_analysis_20241114_045900.json',
        project_root / 'scripts/csvs/virgin/☎️  Radical Planners Database ☎️ - Rad Planners Community List.csv',
        project_root / 'scripts/csvs/virgin/Client_Contact Master - Free Money Podcast Email List.csv',
        project_root / 'scripts/csvs/virgin/List for Sloane.xlsx - FOD V5.csv'
    ]
    
    print("Starting email extraction process...")
    
    # Load existing emails
    existing_emails = load_existing_emails(reference_file)
    print(f"Loaded {len(existing_emails)} existing emails from reference file")
    
    # Process files and compare
    all_emails, new_emails, existing_matches = process_files(files, existing_emails)
    
    # Save results
    save_results(all_emails, new_emails, existing_matches, output_dir)
    
    # Print statistics
    print("\nExtraction Statistics:")
    print(f"Total unique emails found: {len(all_emails)}")
    print(f"New emails found: {len(new_emails)}")
    print(f"Existing emails matched: {len(existing_matches)}")
    
    # Print domain statistics for new emails
    if new_emails:
        print("\nTop 10 domains in new emails:")
        domains = {}
        for email in new_emails:
            domain = email.split('@')[-1].lower()
            domains[domain] = domains.get(domain, 0) + 1
            
        for domain, count in sorted(domains.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"{domain}: {count}")
            
    print(f"\nResults saved to {output_dir}")

if __name__ == "__main__":
    main() 