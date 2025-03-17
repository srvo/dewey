from supabase_client import SupabaseClient
import pandas as pd
import re

def extract_email(from_string: str) -> str:
    """Extract email address from a full From header"""
    match = re.search(r'<([^>]+)>', from_string)
    if match:
        return match.group(1).lower()
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', from_string)
    if match:
        return match.group(0).lower()
    return from_string.lower()

def update_email_contacts():
    try:
        client = SupabaseClient().get_client()
        print("Connected to Supabase")
        
        # First check table structure
        contact_sample = client.table('Contacts').select('*').limit(1).execute()
        print("\nContact table fields:", list(contact_sample.data[0].keys()))
        
        email_sample = client.table('Emails').select('*').limit(1).execute()
        print("Email table fields:", list(email_sample.data[0].keys()))
        
        # Read contacts to process
        df = pd.read_csv('/Users/srvo/lc/performance/output/contact_updates_completed.csv')
        print(f"\nFound {len(df)} contacts to process")
        
        updates = 0
        for _, row in df.iterrows():
            email = row['email'].lower()
            
            try:
                # Get Contact's Entity ID
                contact_result = client.table('Contacts').select('Entity ID').eq('Email', email).execute()
                
                if contact_result.data:
                    entity_id = contact_result.data[0]['Entity ID']
                    print(f"\nProcessing {email}")
                    print(f"Entity ID: {entity_id}")
                    
                    # Find matching emails
                    emails = client.table('Emails').select('id', 'from_address').execute()
                    to_update = []
                    
                    for e in emails.data:
                        extracted = extract_email(e['from_address'])
                        if extracted == email:
                            to_update.append(e['id'])
                    
                    print(f"Found {len(to_update)} emails to update")
                    
                    # Update each email
                    for email_id in to_update:
                        update_result = client.table('Emails') \
                            .update({"contact_id": entity_id}) \
                            .eq('id', email_id) \
                            .execute()
                        
                        if update_result.data:
                            updates += 1
                            print(f"Updated email {email_id}")
            
            except Exception as e:
                print(f"Error processing {email}: {str(e)}")
                continue
        
        print(f"\nTotal emails updated: {updates}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        print(f"Error type: {type(e)}")

if __name__ == "__main__":
    update_email_contacts() 