from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os.path
import pickle
import base64
import json
from openai import OpenAI
import time
from datetime import datetime

# Gmail API setup
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CREDENTIALS_PATH = '/Users/srvo/Data/credentials.json'

def get_gmail_service():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('gmail', 'v1', credentials=creds)

def search_form_and_call_emails(service):
    """Search for emails with specific labels and senders"""
    query = """
        (
            label:call-summary OR 
            subject:"ai recap" OR 
            subject:"notes" OR
            subject:"form entry" OR
            subject:"new form"
        )
        after:2021/09/01
    """
    
    try:
        print(f"Searching with query: {query}")
        results = service.users().messages().list(userId='me', q=query).execute()
        messages = results.get('messages', [])
        
        # Print some example subjects to verify we're getting the right emails
        if messages:
            print("\nSample matches:")
            for msg in messages[:3]:
                email = service.users().messages().get(userId='me', id=msg['id'], format='minimal').execute()
                subject = next((h['value'] for h in email.get('payload', {}).get('headers', []) 
                              if h['name'].lower() == 'subject'), 'No Subject')
                print(f"- {subject}")
                
        return messages
    except Exception as e:
        print(f"Error searching emails: {e}")
        return []

def get_email_content(service, msg_id):
    try:
        message = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
        payload = message['payload']
        headers = payload['headers']
        
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'No Sender')
        date = next((h['value'] for h in headers if h['name'].lower() == 'date'), 'No Date')
        
        parts = []
        if 'parts' in payload:
            parts = payload['parts']
        else:
            parts = [payload]
            
        text = ""
        for part in parts:
            if part.get('mimeType') == 'text/plain':
                if 'data' in part['body']:
                    text += base64.urlsafe_b64decode(part['body']['data']).decode()
                elif 'attachmentId' in part['body']:
                    continue
        
        return {
            'subject': subject,
            'sender': sender,
            'date': date,
            'content': text or "No content available"
        }
    except Exception as e:
        print(f"Error getting email content: {e}")
        return None

def analyze_with_llm(email_data):
    client = OpenAI()
    
    # Clean and truncate content to avoid token limits
    content = email_data['content'][:4000].replace('\n', ' ').replace('"', "'")
    
    system_prompt = """You are a JSON parser for email content. You must ALWAYS return valid JSON.
    If the content is a form submission or call summary, extract the relevant information.
    If you cannot parse the content, return a basic JSON structure with null values."""
    
    user_prompt = f"""Analyze this email:
    Subject: {email_data['subject']}
    From: {email_data['sender']}
    Date: {email_data['date']}
    Labels: {', '.join(email_data.get('labels', []))}
    
    Content: {content}

    Extract the information and return ONLY this exact JSON structure:
    {{
        "type": "form_entry/call_summary/other",
        "details": {{
            "name": null,
            "email": null,
            "phone": null,
            "company": null,
            "form_type": null,
            "submission_date": null
        }},
        "content": {{
            "summary": null,
            "key_points": [],
            "raw_form_data": null
        }},
        "metadata": {{
            "source": null,
            "confidence": "high/medium/low",
            "processed_date": "{datetime.now().isoformat()}"
        }}
    }}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,  # Lower temperature for more consistent output
            response_format={"type": "json_object"},  # Force JSON response
            max_tokens=2000
        )
        
        # Get the response content
        result = response.choices[0].message.content.strip()
        
        # Ensure we have valid JSON
        try:
            parsed_result = json.loads(result)
            return parsed_result
        except json.JSONDecodeError:
            # Return a fallback JSON structure if parsing fails
            return {
                "type": "unknown",
                "details": {
                    "name": None,
                    "email": None,
                    "phone": None,
                    "company": None,
                    "form_type": None,
                    "submission_date": None
                },
                "content": {
                    "summary": "Failed to parse content",
                    "key_points": [],
                    "raw_form_data": None
                },
                "metadata": {
                    "source": email_data['subject'],
                    "confidence": "low",
                    "processed_date": datetime.now().isoformat(),
                    "error": "Failed to parse LLM response"
                }
            }
            
    except Exception as e:
        print(f"LLM API error: {str(e)}")
        # Return a fallback JSON structure for API errors
        return {
            "type": "error",
            "details": {
                "name": None,
                "email": None,
                "phone": None,
                "company": None,
                "form_type": None,
                "submission_date": None
            },
            "content": {
                "summary": f"Error processing content: {str(e)}",
                "key_points": [],
                "raw_form_data": None
            },
            "metadata": {
                "source": email_data['subject'],
                "confidence": "low",
                "processed_date": datetime.now().isoformat(),
                "error": str(e)
            }
        }

def main():
    print("Starting form and transcript search...")
    service = get_gmail_service()
    
    query = """
        (
            label:call-summary OR 
            subject:"ai recap" OR 
            subject:"notes" OR
            subject:"form entry" OR
            subject:"new form"
        )
        after:2021/09/01
    """
    
    print(f"Searching with query: {query}")
    
    # Get all messages with pagination
    messages = []
    next_page_token = None
    
    while True:
        try:
            results = service.users().messages().list(
                userId='me', 
                q=query,
                maxResults=500,
                pageToken=next_page_token
            ).execute()
            
            if 'messages' in results:
                messages.extend(results['messages'])
                print(f"Found {len(messages)} messages so far...")
            
            next_page_token = results.get('nextPageToken')
            if not next_page_token:
                break
                
        except Exception as e:
            print(f"Error fetching messages: {e}")
            break
    
    if not messages:
        print("No matching emails found")
        return
        
    print(f"\nFound total of {len(messages)} relevant emails")
    
    analyzed_data = []
    
    for i, msg in enumerate(messages, 1):
        print(f"\nProcessing email {i}/{len(messages)}")
        
        email_data = get_email_content(service, msg['id'])
        if not email_data:
            print("Failed to get email content")
            continue
            
        print(f"Analyzing: {email_data['subject']}")
        analysis = analyze_with_llm(email_data)
        
        if analysis:
            analyzed_data.append({
                'metadata': {
                    'subject': email_data['subject'],
                    'sender': email_data['sender'],
                    'date': email_data['date'],
                    'labels': email_data.get('labels', [])
                },
                'analysis': analysis
            })
            
        # Save progress every 20 emails
        if i % 20 == 0:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            with open(f'email_analysis_{timestamp}.json', 'w') as f:
                json.dump(analyzed_data, f, indent=2)
            print(f"\nProgress saved - {i} emails processed")
        
        time.sleep(1)  # Rate limiting
    
    # Save final results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    with open(f'email_analysis_{timestamp}.json', 'w') as f:
        json.dump(analyzed_data, f, indent=2)
    
    print(f"\nAnalysis complete! Processed {len(messages)} emails")
    print(f"Results saved to email_analysis_{timestamp}.json")

if __name__ == '__main__':
    main()
