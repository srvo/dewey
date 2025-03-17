import json
import csv
from pathlib import Path
from datetime import datetime
import argparse

def flatten_email_data(email_address, email_entries):
    """Flatten email data into rows for CSV"""
    flattened_rows = []
    
    for entry in email_entries:
        row = {
            'email_address': email_address,
            'subject': entry.get('subject', ''),
            'sender': entry.get('sender', ''),
            'recipient': entry.get('recipient', ''),
            'date': entry.get('date', ''),
            'message_id': entry.get('message_id', ''),
            'thread_id': entry.get('thread_id', ''),
            # Clean and truncate content
            'content': entry.get('content', '').replace('\r\n', ' ').replace('\n', ' ')[:500] if entry.get('content') else ''
        }
        flattened_rows.append(row)
    
    return flattened_rows

def convert_json_to_csv(input_file, output_dir):
    """Convert email analysis JSON to CSV format"""
    # Read JSON file
    print(f"Reading JSON from: {input_file}")
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    # Prepare rows for CSV
    rows = []
    for email_address, email_entries in data.items():
        rows.extend(flatten_email_data(email_address, email_entries))
    
    if not rows:
        print("No data to convert")
        return
    
    # Create output directory if it doesn't exist
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f'email_analysis_{timestamp}.csv'
    
    # Write to CSV
    fieldnames = rows[0].keys()
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    return output_file

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Convert email analysis JSON to CSV')
    parser.add_argument('input_file', type=str, help='Path to input JSON file')
    parser.add_argument('--output-dir', type=str, default='output',
                      help='Output directory (default: output)')
    
    args = parser.parse_args()
    
    # Convert paths to Path objects
    input_file = Path(args.input_file)
    output_dir = Path(args.output_dir)
    
    print(f"Converting {input_file} to CSV format...")
    
    try:
        output_file = convert_json_to_csv(input_file, output_dir)
        print(f"Successfully converted to CSV: {output_file}")
        
        # Print some statistics
        with open(output_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
        unique_emails = len(set(row['email_address'] for row in rows))
        total_messages = len(rows)
        
        print("\nConversion Statistics:")
        print(f"Total unique email addresses: {unique_emails}")
        print(f"Total email messages: {total_messages}")
        print(f"Average messages per email: {total_messages/unique_emails:.1f}")
        
    except Exception as e:
        print(f"Error converting file: {str(e)}")
        raise

if __name__ == "__main__":
    main() 