from supabase import create_client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

def verify_import():
    print("\nVerifying import...")
    
    # Check companies count
    companies = supabase.table('companies').select('count', count='exact').execute()
    print(f"Total companies: {companies.count}")
    
    # Check tick history count
    tick_history = supabase.table('tick_history').select('count', count='exact').execute()
    print(f"Total tick history records: {tick_history.count}")
    
    # Check research notes count
    notes = supabase.table('research_notes').select('count', count='exact').execute()
    print(f"Total research notes: {notes.count}")
    
    # Sample some exclusion notes
    exclusions = supabase.table('research_notes')\
        .select('ticker,content,created_at')\
        .eq('note_type', 'exclusion')\
        .limit(5)\
        .execute()
    
    print("\nSample exclusion notes:")
    for note in exclusions.data:
        print(f"\nTicker: {note['ticker']}")
        print(f"Content: {note['content'][:100]}...")
        print(f"Created: {note['created_at']}")

if __name__ == "__main__":
    verify_import()