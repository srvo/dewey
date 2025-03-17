from supabase_client import SupabaseClient
import re

def extract_email(from_string: str) -> str:
    """Extract clean email address from a full From header"""
    # Try to find email in <brackets>
    match = re.search(r'<([^>]+)>', from_string)
    if match:
        return match.group(1).lower()
    
    # If no brackets, try to find anything that looks like an email
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', from_string)
    if match:
        return match.group(0).lower()
    
    return from_string.lower()

def clean_email_addresses():
    try:
        client = SupabaseClient().get_client()
        print("Connected to Supabase")
        
        # Get all emails
        result = client.table('Emails').select('id', 'from_address').execute()
        print(f"Found {len(result.data)} emails to process")
        
        # Process a few examples first
        print("\nSample conversions:")
        for i, email in enumerate(result.data[:5]):
            from_address = email['from_address']
            clean_email = extract_email(from_address)
            print(f"{from_address} -> {clean_email}")
        
        proceed = input("\nProceed with updating all emails? (y/n): ")
        if proceed.lower() != 'y':
            print("Aborting.")
            return
        
        # Update all emails
        updates = 0
        for email in result.data:
            try:
                clean_email = extract_email(email['from_address'])
                
                update_result = client.table('Emails') \
                    .update({"from_email": clean_email}) \
                    .eq('id', email['id']) \
                    .execute()
                
                if update_result.data:
                    updates += 1
                    if updates % 100 == 0:
                        print(f"Updated {updates} emails...")
            
            except Exception as e:
                print(f"Error updating email {email['id']}: {str(e)}")
                continue
        
        print(f"\nTotal emails updated: {updates}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        print(f"Error type: {type(e)}")

if __name__ == "__main__":
    clean_email_addresses() 