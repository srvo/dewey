from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import base64
import os
import datetime
import email
import time

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return build('gmail', 'v1', credentials=creds)

def get_email_content(service, msg_id):
    try:
        message = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
        payload = message['payload']
        headers = payload['headers']
        
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '(No Subject)')
        date = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
        from_email = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')
        
        parts = payload.get('parts', [])
        body = ''
        
        if 'body' in payload and 'data' in payload['body']:
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='replace')
        else:
            for part in parts:
                if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='replace')
                    break
        
        return {
            'subject': subject,
            'date': date,
            'from': from_email,
            'body': body
        }
    except Exception as e:
        print(f"Error processing message {msg_id}: {e}")
        return None

def main():
    service = get_gmail_service()
    
    # Create output directory
    if not os.path.exists('email_archive'):
        os.makedirs('email_archive')
    
    # Track progress
    processed_count = 0
    page_token = None
    
    while True:
        try:
            # Get batch of messages with pagination
            results = service.users().messages().list(
                userId='me',
                maxResults=500,  # Max allowed by Gmail API
                pageToken=page_token,
                q='in:anywhere'  # Search all emails, including spam and trash
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                break
                
            total_in_batch = len(messages)
            print(f"\nProcessing batch of {total_in_batch} messages...")
            
            # Process each message in the batch
            for idx, message in enumerate(messages, 1):
                try:
                    email_data = get_email_content(service, message['id'])
                    if email_data:
                        try:
                            date = email.utils.parsedate_to_datetime(email_data['date'])
                        except:
                            # If date parsing fails, use current time
                            date = datetime.datetime.now()
                            
                        month_year = date.strftime('%Y-%m')
                        
                        # Create month directory if it doesn't exist
                        month_dir = f'email_archive/{month_year}'
                        if not os.path.exists(month_dir):
                            os.makedirs(month_dir)
                        
                        # Write email to file
                        filename = f"{month_dir}/{date.strftime('%Y%m%d_%H%M%S')}_{message['id']}.txt"
                        with open(filename, 'w', encoding='utf-8', errors='replace') as f:
                            f.write(f"Subject: {email_data['subject']}\n")
                            f.write(f"From: {email_data['from']}\n")
                            f.write(f"Date: {email_data['date']}\n")
                            f.write("\n")
                            f.write(email_data['body'])
                        
                        processed_count += 1
                        if processed_count % 100 == 0:
                            print(f"Processed {processed_count} emails...")
                
                except Exception as e:
                    print(f"Error saving message {message['id']}: {e}")
                    continue
                
                # Sleep briefly to avoid hitting API limits
                if idx % 100 == 0:
                    time.sleep(2)
            
            # Get next page token
            page_token = results.get('nextPageToken')
            if not page_token:
                break
                
        except Exception as e:
            print(f"Error processing batch: {e}")
            time.sleep(60)  # Wait longer if we hit an error
            continue
    
    print(f"\nComplete! Processed {processed_count} emails total.")

if __name__ == '__main__':
    main()
