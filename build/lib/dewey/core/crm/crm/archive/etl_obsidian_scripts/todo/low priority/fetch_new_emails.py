import wmill
from supabase import create_client, Client
import time
from datetime import datetime, timezone

def get_latest_email_date(supabase):
    """Get the most recent email date in our database"""
    result = supabase.table('Emails')\
        .select('sent_date')\
        .order('sent_date', desc=True)\
        .limit(1)\
        .execute()
    
    if result.data:
        return result.data[0]['sent_date']
    return None

def main():
    start_time = time.time()
    
    # Get Supabase credentials from Windmill resource
    supabase_creds = wmill.get_resource("u/sloane/warmhearted_supabase")
    supabase = create_client(supabase_creds['url'], supabase_creds['service_role_key'])
    
    # Get Gmail credentials and initialize Gmail API client
    gmail_creds = wmill.get_resource("u/sloane/gmail")
    # TODO: Initialize Gmail client with credentials
    
    # Get the latest email date from our database
    latest_db_date = get_latest_email_date(supabase)
    print(f"Latest email in database: {latest_db_date}")
    
    # Fetch new emails from Gmail
    new_emails = []
    # TODO: Implement Gmail fetch logic
    
    # Insert new emails into Supabase
    inserted = 0
    for email in new_emails:
        try:
            supabase.table('Emails')\
                .insert({
                    'subject': email['subject'],
                    'body': email['body'],
                    'sent_date': email['sent_date'],
                    'from_address': email['from_address'],
                    'from_email': email['from_email'],
                    'to_addresses': email['to_addresses'],
                    'cc_addresses': email['cc_addresses'],
                    'thread_id': email['thread_id'],
                    'labels': email['labels']
                })\
                .execute()
            inserted += 1
            
            if inserted % 100 == 0:
                print(f"Inserted {inserted} new emails...")
                
        except Exception as e:
            print(f"Error inserting email: {str(e)}")
    
    elapsed_time = time.time() - start_time
    return {
        "new_emails_found": len(new_emails),
        "emails_inserted": inserted,
        "time_elapsed": f"{elapsed_time:.1f} seconds",
        "latest_db_date": latest_db_date
    }

if __name__ == "__main__":
    result = main()
    print(result)