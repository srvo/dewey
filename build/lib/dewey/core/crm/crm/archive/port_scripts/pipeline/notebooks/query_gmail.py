from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from pathlib import Path
import os.path
import pickle
import base64
import email
import json
from openai import OpenAI
import time
from datetime import datetime
import sys

# Gmail API setup
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
PROJECT_ROOT = Path(__file__).parent.parent
CREDENTIALS_PATH = PROJECT_ROOT / 'credentials.json'
OUTPUT_DIR = PROJECT_ROOT / 'output'
EMAILS_FILE = PROJECT_ROOT / 'unique_emails.txt'
BATCH_SIZE = 50  # Number of emails to process before saving
RATE_LIMIT_DELAY = 1  # Seconds between API calls

def load_progress():
    """Load previously processed emails"""
    progress_file = OUTPUT_DIR / 'processed_emails.json'
    if progress_file.exists():
        with open(progress_file, 'r') as f:
            return json.load(f)
    return {}

def save_progress(processed):
    """Save progress of processed emails"""
    progress_file = OUTPUT_DIR / 'processed_emails.json'
    with open(progress_file, 'w') as f:
        json.dump(processed, f, indent=2)

def get_gmail_service():
    """Initialize and return Gmail API service"""
    creds = None
    token_path = PROJECT_ROOT / 'token.pickle'
    
    if token_path.exists():
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    return build('gmail', 'v1', credentials=creds)

def search_emails(service, email_address, max_results=50):
    """Search for emails to/from an address with pagination"""
    all_messages = []
    try:
        request = service.users().messages().list(
            userId='me',
            q=f"from:{email_address} OR to:{email_address}",
            maxResults=max_results
        )
        
        while request is not None:
            response = request.execute()
            messages = response.get('messages', [])
            all_messages.extend(messages)
            
            request = service.users().messages().list_next(request, response)
            if len(all_messages) >= max_results:
                break
                
        return all_messages[:max_results]
    except Exception as e:
        print(f"Error searching for {email_address}: {e}")
        return []

def get_email_content(service, msg_id):
    """Get content of a specific email"""
    try:
        message = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
        payload = message['payload']
        headers = payload['headers']
        
        # Extract headers
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'No Sender')
        date = next((h['value'] for h in headers if h['name'].lower() == 'date'), 'No Date')
        to = next((h['value'] for h in headers if h['name'].lower() == 'to'), 'No Recipient')
        
        # Extract body
        text = ""
        if 'parts' in payload:
            parts = payload['parts']
        else:
            parts = [payload]
            
        for part in parts:
            if part.get('mimeType') == 'text/plain':
                if 'data' in part['body']:
                    text += base64.urlsafe_b64decode(part['body']['data']).decode()
                elif 'attachmentId' in part['body']:
                    continue
        
        return {
            'subject': subject,
            'sender': sender,
            'recipient': to,
            'date': date,
            'content': text or "No content available",
            'message_id': msg_id,
            'thread_id': message.get('threadId', '')
        }
    except Exception as e:
        print(f"Error getting email content for message {msg_id}: {e}")
        return None

def process_email_batch(service, email_addresses, processed_data):
    """Process a batch of email addresses"""
    results = {}
    
    for email_address in email_addresses:
        if email_address in processed_data:
            print(f"Skipping already processed: {email_address}")
            continue
            
        print(f"\nProcessing: {email_address}")
        messages = search_emails(service, email_address)
        
        if messages:
            print(f"Found {len(messages)} messages")
            email_results = []
            
            for msg in messages[:5]:  # Process up to 5 most recent emails
                email_data = get_email_content(service, msg['id'])
                if email_data:
                    email_results.append(email_data)
                time.sleep(RATE_LIMIT_DELAY)
            
            if email_results:
                results[email_address] = email_results
                print(f"Successfully processed {len(email_results)} messages")
        else:
            print("No messages found")
        
        time.sleep(RATE_LIMIT_DELAY)
    
    return results

def save_batch_results(results, batch_num):
    """Save results for a batch of processed emails"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save detailed results
    batch_file = OUTPUT_DIR / f'email_analysis_batch_{batch_num}_{timestamp}.json'
    with open(batch_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Update master results file
    master_file = OUTPUT_DIR / 'email_analysis_master.json'
    if master_file.exists():
        with open(master_file, 'r') as f:
            master_data = json.load(f)
    else:
        master_data = {}
    
    master_data.update(results)
    
    with open(master_file, 'w') as f:
        json.dump(master_data, f, indent=2)

def main():
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("Starting Gmail analysis...")
    
    # Initialize Gmail service
    service = get_gmail_service()
    
    # Load email addresses
    try:
        with open(EMAILS_FILE, 'r') as f:
            email_addresses = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"Error loading email addresses: {e}")
        return
    
    print(f"Loaded {len(email_addresses)} email addresses")
    
    # Load previously processed emails
    processed_data = load_progress()
    remaining_emails = [e for e in email_addresses if e not in processed_data]
    
    print(f"Found {len(processed_data)} previously processed emails")
    print(f"{len(remaining_emails)} emails remaining to process")
    
    # Process in batches
    for i in range(0, len(remaining_emails), BATCH_SIZE):
        batch_num = (i // BATCH_SIZE) + 1
        batch = remaining_emails[i:i + BATCH_SIZE]
        print(f"\nProcessing batch {batch_num} ({len(batch)} emails)")
        
        results = process_email_batch(service, batch, processed_data)
        
        # Save batch results
        if results:
            save_batch_results(results, batch_num)
            processed_data.update(results)
            save_progress(processed_data)
            
        print(f"Completed batch {batch_num}")
        print(f"Progress: {len(processed_data)}/{len(email_addresses)} emails processed")
        
        # Optional: Add a longer delay between batches
        if i + BATCH_SIZE < len(remaining_emails):
            print("Pausing between batches...")
            time.sleep(5)
    
    print("\nAnalysis complete!")
    print(f"Processed {len(processed_data)} total emails")
    print(f"Results saved to {OUTPUT_DIR}")

if __name__ == '__main__':
    main()