from supabase_client import SupabaseClient
import pandas as pd
import re

def extract_email(from_string: str) -> str:
    """Extract email address from a full From header"""
    # Try to find email in <brackets>
    match = re.search(r'<([^>]+)>', from_string)
    if match:
        return match.group(1).lower()
    
    # If no brackets, try to find anything that looks like an email
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', from_string)
    if match:
        return match.group(0).lower()
    
    return from_string.lower()

def update_email_clients():
    try:
        client = SupabaseClient().get_client()
        print("Connected to Supabase")
        
        # Read the successful updates file
        df = pd.read_csv('/Users/srvo/lc/performance/output/contact_updates_completed.csv')
        print(f"Found {len(df)} successfully updated contacts")
        
        # Get all emails for these contacts
        updates = 0
        for _, row in df.iterrows():
            email = row['email'].lower()
            
            try:
                # Get the contact's Entity ID
                contact_result = client.table('Contacts').select('Entity ID').eq('Email', email).execute()
                
                if contact_result.data:
                    # Convert hex ID to UUID format
                    raw_id = contact_result.data[0]['Entity ID']
                    entity_id = f"{raw_id.lower()}-0000-0000-0000-000000000000"
                    
                    print(f"\nProcessing {email}")
                    print(f"Entity ID: {entity_id}")
                    
                    # Find emails where the from_address contains this email
                    emails = client.table('Emails').select('id', 'from_address', 'client_id').execute()
                    to_update = []
                    
                    for e in emails.data:
                        extracted = extract_email(e['from_address'])
                        if extracted == email:
                            to_update.append(e['id'])
                    
                    print(f"Found {len(to_update)} emails to update")
                    
                    # Update each email
                    for email_id in to_update:
                        update_result = client.table('Emails') \
                            .update({"client_id": entity_id}) \
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
    update_email_clients() 