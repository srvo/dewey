from supabase_client import SupabaseClient
import pandas as pd
import re

def clean_name(name: str) -> str:
    """Clean up suggested names from Gmail"""
    if not name or name == 'Unknown':
        return None
        
    # Remove quotes and email addresses
    name = re.sub(r'^["\']+|["\']+$', '', name)  # Remove surrounding quotes
    name = re.sub(r'<.*?>', '', name)  # Remove email addresses
    name = re.sub(r'\|.*$', '', name)  # Remove everything after |
    
    # Remove specific patterns
    name = name.replace('@yahoo.co.uk', '')
    
    # Clean up common prefixes
    prefixes = ['"', "'"]
    for prefix in prefixes:
        if name.startswith(prefix):
            name = name[1:]
        if name.endswith(prefix):
            name = name[:-1]
            
    return name.strip()

def update_contacts():
    try:
        # Read the CSV file
        df = pd.read_csv('/Users/srvo/lc/performance/output/contacts_to_fix_gmail.csv')
        
        # Connect to Supabase
        client = SupabaseClient().get_client()
        print("Connected to Supabase")
        
        # Track updates
        updates = []
        skipped = []
        
        # Process each row
        for _, row in df.iterrows():
            entity_id = row['id']
            current_name = row['current_name']
            suggested_name = clean_name(row['suggested_name'])
            email = row['email']
            
            if suggested_name:
                try:
                    # Update only the name
                    client.table('Contacts').update({
                        'full_name': suggested_name
                    }).eq('Entity ID', entity_id).execute()
                    
                    updates.append({
                        'email': email,
                        'old_name': current_name,
                        'new_name': suggested_name
                    })
                    print(f"Updated: {email} -> {suggested_name}")
                    
                except Exception as e:
                    print(f"Error updating {email}: {str(e)}")
                    skipped.append({
                        'email': email,
                        'current_name': current_name,
                        'reason': str(e)
                    })
            else:
                skipped.append({
                    'email': email,
                    'current_name': current_name,
                    'reason': 'No suggested name'
                })
        
        # Save results
        if updates:
            pd.DataFrame(updates).to_csv('/Users/srvo/lc/performance/output/contact_updates_completed.csv', index=False)
            print(f"\nUpdated {len(updates)} contacts")
            
        if skipped:
            pd.DataFrame(skipped).to_csv('/Users/srvo/lc/performance/output/contact_updates_skipped.csv', index=False)
            print(f"Skipped {len(skipped)} contacts")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        print(f"Error type: {type(e)}")

if __name__ == "__main__":
    update_contacts() 