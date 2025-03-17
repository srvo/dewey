import wmill
from supabase import create_client
from google.oauth2 import service_account
from googleapiclient.discovery import build
import base64
import email
from email.utils import parseaddr, parsedate_to_datetime
import time
from datetime import datetime

# Define the resource type for Supabase
supabase_resource_type = "supabase"

def get_gmail_service():
    """Get authenticated Gmail service using service account"""
    credentials_json = wmill.get_resource("u/sloane/lavish_c_gmail_service_account")
    
    # Print the service account email for verification
    print(f"Using service account: {credentials_json.get('client_email', 'Not found')}")
    
    credentials = service_account.Credentials.from_service_account_info(
        credentials_json,
        scopes=['https://www.googleapis.com/auth/gmail.readonly'],
        subject="sloane@srvo.org"
    )
    
    return build('gmail', 'v1', credentials=credentials)

def get_existing_thread_ids(supabase_client):
    """Get all existing thread IDs to avoid duplicates"""
    all_threads = set()
    page = 0
    page_size = 1000
    
    while True:
        result = supabase_client.table('Emails')\
            .select('thread_id')\
            .range(page * page_size, (page + 1) * page_size - 1)\
            .execute()
        
        if not result.data:
            break
            
        all_threads.update(r['thread_id'] for r in result.data if r.get('thread_id'))
        page += 1
        print(f"Fetched {len(all_threads)} existing thread IDs...")
    
    return all_threads

def extract_email_address(address_string):
    """Extract email address from various formats"""
    if not address_string:
        return None
    _, email_addr = parseaddr(address_string)
    return email_addr.lower() if email_addr else None

def process_addresses(addresses):
    """Process list of email addresses"""
    if not addresses:
        return None
    return [addr for addr in addresses if addr]

def get_email_body(message):
    """Extract email body from message"""
    if 'parts' in message['payload']:
        for part in message['payload']['parts']:
            if part['mimeType'] == 'text/plain':
                return base64.urlsafe_b64decode(part['body']['data']).decode()
    elif 'body' in message['payload']:
        return base64.urlsafe_b64decode(message['payload']['body']['data']).decode()
    return None

def parse_email_date(date_str):
    """Convert email date string to ISO format"""
    try:
        # Parse the email date format
        dt = parsedate_to_datetime(date_str)
        # Convert to ISO format
        return dt.isoformat()
    except Exception:
        return None

def main():
    start_time = time.time()
    
    try:
        # Get Supabase credentials
        supabase_creds = wmill.get_resource("u/sloane/warmhearted_supabase")
        
        # Create Supabase client with the correct field names
        supabase_client = create_client(
            supabase_creds['url'],
            supabase_creds['key']
        )
        
        # Initialize Gmail
        print("\nInitializing Gmail service...")
        gmail = get_gmail_service()
        
        # Get existing thread IDs
        print("Fetching existing thread IDs...")
        existing_threads = get_existing_thread_ids(supabase_client)
        print(f"Found {len(existing_threads)} existing threads")
        
        # Test Gmail API access
        print("Testing Gmail API access...")
        try:
            results = gmail.users().messages().list(
                userId='me',
                maxResults=1
            ).execute()
            print("Successfully accessed Gmail API")
        except Exception as e:
            print(f"Gmail API error: {str(e)}")
            raise
            
        # Process emails in batches
        processed = 0
        inserted = 0
        page_token = None
        
        while True:
            try:
                # Get list of messages
                results = gmail.users().messages().list(
                    userId='me',
                    maxResults=100,
                    pageToken=page_token
                ).execute()
                
                messages = results.get('messages', [])
                
                if not messages:
                    break
                    
                # Process each message
                for msg_meta in messages:
                    processed += 1
                    
                    # Skip if thread already exists
                    if msg_meta['threadId'] in existing_threads:
                        continue
                    
                    # Get full message details
                    msg = gmail.users().messages().get(
                        userId='me',
                        id=msg_meta['id'],
                        format='full'
                    ).execute()
                    
                    # Extract headers
                    headers = msg['payload']['headers']
                    header_dict = {h['name'].lower(): h['value'] for h in headers}
                    
                    # Process email addresses
                    from_email = extract_email_address(header_dict.get('from'))
                    to_addresses = process_addresses([
                        extract_email_address(addr.strip())
                        for addr in header_dict.get('to', '').split(',')
                    ])
                    cc_addresses = process_addresses([
                        extract_email_address(addr.strip())
                        for addr in header_dict.get('cc', '').split(',')
                    ]) if 'cc' in header_dict else None
                    
                    # Insert into Supabase
                    try:
                        supabase_client.table('Emails').insert({
                            'thread_id': msg['threadId'],
                            'subject': header_dict.get('subject'),
                            'body': get_email_body(msg),
                            'sent_date': parse_email_date(header_dict.get('date')),
                            'from_address': header_dict.get('from'),
                            'from_email': from_email,
                            'to_addresses': to_addresses,
                            'cc_addresses': cc_addresses,
                            'labels': msg['labelIds']
                        }).execute()
                        
                        inserted += 1
                        existing_threads.add(msg['threadId'])
                        
                    except Exception as e:
                        print(f"Error inserting message {msg_meta['id']}: {str(e)}")
                    
                    if processed % 100 == 0:
                        print(f"Processed {processed} messages, inserted {inserted} new ones...")
                
                # Get next page
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
                    
            except Exception as e:
                print(f"Error processing page: {str(e)}")
                break
        
        elapsed_time = time.time() - start_time
        return {
            "messages_processed": processed,
            "new_messages_inserted": inserted,
            "time_elapsed": f"{elapsed_time:.1f} seconds"
        }

    except Exception as e:
        print(f"Main error: {str(e)}")
        print(f"Error type: {type(e)}")
        raise

if __name__ == "__main__":
    result = main()
    print(result)
