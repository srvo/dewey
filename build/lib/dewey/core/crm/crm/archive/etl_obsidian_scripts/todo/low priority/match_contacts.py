import wmill
from supabase import create_client, Client

def main(
    workspace_id: str = wmill.get_workspace(),
    supabase_url: str = wmill.get_resource("supabase_url"),
    supabase_key: str = wmill.get_resource("supabase_key")
):
    # Initialize Supabase client
    supabase: Client = create_client(supabase_url, supabase_key)
    
    # Get all unmatched emails
    emails = supabase.table('emails')\
        .select('id, address')\
        .is_('contact_id', 'null')\
        .execute()
    
    # Get all contacts
    contacts = supabase.table('contacts')\
        .select('uuid, email')\
        .execute()
    
    # Create lookup dictionary
    contact_map = {contact['email'].lower(): contact['uuid'] 
                  for contact in contacts.data 
                  if contact.get('email')}
    
    # Match and update
    for email in emails.data:
        email_address = email['address'].lower()
        if email_address in contact_map:
            supabase.table('emails')\
                .update({'contact_id': contact_map[email_address]})\
                .eq('id', email['id'])\
                .execute()
    
    return "Email matching completed"
