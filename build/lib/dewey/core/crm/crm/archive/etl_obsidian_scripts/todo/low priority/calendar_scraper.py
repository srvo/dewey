import os
import pickle
from datetime import datetime, timezone, UTC, timedelta
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pandas as pd
import duckdb
from pathlib import Path
from dotenv import load_dotenv

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def get_google_calendar_service():
    """Get or refresh Google Calendar credentials"""
    creds = None
    
    # Look for token in current directory and .ipynb_checkpoints
    token_paths = [
        'token.pickle',
        '.ipynb_checkpoints/calendar/token.pickle',
        '.ipynb_checkpoints/token.pickle'
    ]
    
    # Look for credentials in current directory and .ipynb_checkpoints
    cred_paths = [
        'credentials.json',
        '.ipynb_checkpoints/calendar/credentials.json',
        '.ipynb_checkpoints/credentials.json'
    ]
    
    # Try to load existing token
    for token_path in token_paths:
        if os.path.exists(token_path):
            print(f"Loading token from {token_path}")
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
            break
    
    # If credentials need refresh or don't exist
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing credentials...")
            creds.refresh(Request())
        else:
            # Look for credentials file
            cred_file = None
            for cred_path in cred_paths:
                if os.path.exists(cred_path):
                    print(f"Using credentials from {cred_path}")
                    cred_file = cred_path
                    break
            
            if not cred_file:
                raise FileNotFoundError("No credentials.json found in any expected location")
            
            flow = InstalledAppFlow.from_client_secrets_file(cred_file, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    try:
        service = build('gmail', 'v1', credentials=creds)
        service = build('calendar', 'v3', credentials=creds)
        return service
    except Exception as e:
        print(f"Error building service: {str(e)}")
        return None

def fetch_calendar_data(lookback_days=1200):
    """Modified version of existing function to store raw events"""
    service = get_google_calendar_service()
    
    if service is None:
        print("Failed to initialize Google Calendar service")
        return pd.DataFrame(), []
    
    # Calculate time range using timezone-aware datetime
    now = datetime.now(UTC)
    start_time = (now - timedelta(days=lookback_days)).isoformat()
    end_time = now.isoformat()
    
    print(f"Fetching calendar events from {start_time} to {end_time}")
    
    try:
        all_attendees = []
        all_events = []  # Store raw events
        page_token = None
        total_events = 0
        
        while True:
            events_result = service.events().list(
                calendarId='primary',
                timeMin=start_time,
                timeMax=end_time,
                maxResults=2500,
                singleEvents=True,
                orderBy='startTime',
                pageToken=page_token
            ).execute()
            
            events = events_result.get('items', [])
            all_events.extend(events)  # Store raw events
            total_events += len(events)
            print(f"Fetched {total_events} events...")
            
            for event in events:
                # Get organizer
                if 'organizer' in event:
                    organizer = {
                        'email': event['organizer'].get('email', ''),
                        'name': event['organizer'].get('displayName', ''),
                        'source': 'organizer',
                        'event_id': event['id'],
                        'event_summary': event.get('summary', ''),
                        'event_time': event.get('start', {}).get('dateTime', event.get('start', {}).get('date', '')),
                    }
                    all_attendees.append(organizer)
                
                # Get attendees
                for attendee in event.get('attendees', []):
                    attendee_info = {
                        'email': attendee.get('email', ''),
                        'name': attendee.get('displayName', ''),
                        'source': 'attendee',
                        'event_id': event['id'],
                        'event_summary': event.get('summary', ''),
                        'event_time': event.get('start', {}).get('dateTime', event.get('start', {}).get('date', '')),
                    }
                    all_attendees.append(attendee_info)
            
            page_token = events_result.get('nextPageToken')
            if not page_token:
                break
        
        print(f"Total events fetched: {total_events}")
        
        # Convert to DataFrame
        df = pd.DataFrame(all_attendees)
        
        # Clean and deduplicate
        if not df.empty:
            df['email'] = df['email'].str.lower().str.strip()
            df['domain'] = df['email'].str.split('@').str[1]
            df['event_time'] = pd.to_datetime(df['event_time'])
            
            # Get most recent interaction for each email
            df = df.sort_values('event_time', ascending=False).drop_duplicates(subset=['email'], keep='first')
            
            print(f"\nUnique contacts found: {len(df)}")
            print("\nTop domains:")
            print(df['domain'].value_counts().head(10))
            
            print("\nSource distribution:")
            print(df['source'].value_counts())
        
        return df, all_events  # Return both DataFrame and raw events
        
    except Exception as e:
        print(f"Error fetching calendar data: {str(e)}")
        return pd.DataFrame(), []

def write_contacts_to_duckdb(df, db_path='contacts.duckdb'):
    """
    Write unique calendar contacts to DuckDB with deduplication
    """
    if df.empty:
        print("No contacts to write to database")
        return
    
    try:
        # Connect to DuckDB
        con = duckdb.connect(db_path)
        
        # Create table if it doesn't exist
        con.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                email VARCHAR,
                name VARCHAR,
                domain VARCHAR,
                source VARCHAR,
                event_id VARCHAR,
                event_summary VARCHAR,
                event_time TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(email)
            )
        """)
        
        # Insert new records with conflict resolution
        con.execute("""
            WITH new_contacts AS (
                SELECT 
                    LOWER(TRIM(email)) as email,
                    name,
                    domain,
                    source,
                    event_id,
                    event_summary,
                    event_time::TIMESTAMP as event_time
                FROM df
                WHERE email IS NOT NULL
                AND email != ''
            )
            INSERT OR REPLACE INTO contacts (
                email, name, domain, source, 
                event_id, event_summary, event_time
            )
            SELECT 
                email, name, domain, source,
                event_id, event_summary, event_time
            FROM new_contacts
        """)
        
        # Verify the insertion
        result = con.execute("""
            SELECT 
                COUNT(*) as total_contacts,
                COUNT(DISTINCT domain) as unique_domains,
                COUNT(DISTINCT source) as unique_sources,
                MIN(event_time) as earliest_event,
                MAX(event_time) as latest_event
            FROM contacts
        """).fetchdf()
        
        print("\nDatabase Statistics:")
        print(result)
        
        # Show domain distribution
        print("\nTop Domains in Database:")
        domains = con.execute("""
            SELECT 
                domain,
                COUNT(*) as count,
                COUNT(*) * 100.0 / (SELECT COUNT(*) FROM contacts) as percentage
            FROM contacts
            GROUP BY domain
            ORDER BY count DESC
            LIMIT 10
        """).fetchdf()
        print(domains)
        
        # Show source distribution
        print("\nSource Distribution:")
        sources = con.execute("""
            SELECT 
                source,
                COUNT(*) as count
            FROM contacts
            GROUP BY source
            ORDER BY count DESC
        """).fetchdf()
        print(sources)
        
    except Exception as e:
        print(f"Error writing to database: {str(e)}")
    finally:
        con.close()

def write_events_to_duckdb(events, db_path='contacts.duckdb'):
    """
    Write all calendar events to DuckDB with their full details
    """
    if not events:
        print("No events to write to database")
        return
    
    try:
        # Convert events to DataFrame with flattened structure
        events_data = []
        for event in events:
            event_data = {
                'event_id': event.get('id'),
                'summary': event.get('summary', ''),
                'description': event.get('description', ''),
                'location': event.get('location', ''),
                'start_time': event.get('start', {}).get('dateTime', event.get('start', {}).get('date', '')),
                'end_time': event.get('end', {}).get('dateTime', event.get('end', {}).get('date', '')),
                'created': event.get('created', ''),
                'updated': event.get('updated', ''),
                'status': event.get('status', ''),
                'organizer_email': event.get('organizer', {}).get('email', ''),
                'organizer_name': event.get('organizer', {}).get('displayName', ''),
                'attendee_count': len(event.get('attendees', [])),
                'is_recurring': bool(event.get('recurringEventId')),
                'recurring_event_id': event.get('recurringEventId', ''),
                'calendar_id': event.get('organizer', {}).get('email', ''),
                'html_link': event.get('htmlLink', ''),
                'hangout_link': event.get('hangoutLink', ''),
                'conference_data': str(event.get('conferenceData', {})),
                'visibility': event.get('visibility', 'default'),
                'response_status': event.get('responseStatus', '')
            }
            events_data.append(event_data)
        
        df_events = pd.DataFrame(events_data)
        
        # Connect to DuckDB
        con = duckdb.connect(db_path)
        
        # Create events table if it doesn't exist
        con.execute("""
            CREATE TABLE IF NOT EXISTS calendar_events (
                event_id VARCHAR PRIMARY KEY,
                summary VARCHAR,
                description VARCHAR,
                location VARCHAR,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                created TIMESTAMP,
                updated TIMESTAMP,
                status VARCHAR,
                organizer_email VARCHAR,
                organizer_name VARCHAR,
                attendee_count INTEGER,
                is_recurring BOOLEAN,
                recurring_event_id VARCHAR,
                calendar_id VARCHAR,
                html_link VARCHAR,
                hangout_link VARCHAR,
                conference_data VARCHAR,
                visibility VARCHAR,
                response_status VARCHAR,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert or update events
        con.execute("""
            INSERT OR REPLACE INTO calendar_events (
                event_id, summary, description, location, 
                start_time, end_time, created, updated,
                status, organizer_email, organizer_name, 
                attendee_count, is_recurring, recurring_event_id,
                calendar_id, html_link, hangout_link,
                conference_data, visibility, response_status
            )
            SELECT 
                event_id, summary, description, location,
                start_time::TIMESTAMP, end_time::TIMESTAMP, 
                created::TIMESTAMP, updated::TIMESTAMP,
                status, organizer_email, organizer_name,
                attendee_count, is_recurring, recurring_event_id,
                calendar_id, html_link, hangout_link,
                conference_data, visibility, response_status
            FROM df_events
        """)
        
        # Verify the insertion
        result = con.execute("""
            SELECT 
                COUNT(*) as total_events,
                COUNT(DISTINCT organizer_email) as unique_organizers,
                MIN(start_time) as earliest_event,
                MAX(end_time) as latest_event,
                SUM(CASE WHEN is_recurring THEN 1 ELSE 0 END) as recurring_events,
                AVG(attendee_count) as avg_attendees
            FROM calendar_events
        """).fetchdf()
        
        print("\nEvents Database Statistics:")
        print(result)
        
        # Show event distribution by month
        print("\nEvents by Month:")
        monthly_stats = con.execute("""
            SELECT 
                DATE_TRUNC('month', start_time) as month,
                COUNT(*) as event_count,
                AVG(attendee_count) as avg_attendees
            FROM calendar_events
            GROUP BY DATE_TRUNC('month', start_time)
            ORDER BY month DESC
            LIMIT 12
        """).fetchdf()
        print(monthly_stats)
        
    except Exception as e:
        print(f"Error writing events to database: {str(e)}")
        print("Full error details:", e.__class__.__name__)
    finally:
        con.close()

def upload_to_motherduck(db_path='contacts.duckdb'):
    """
    Upload calendar data to MotherDuck using environment variables
    """
    import os
    from dotenv import load_dotenv
    from pathlib import Path
    
    # Load environment variables from the specific .env file
    env_path = Path("/Users/srvo/Development/.ipynb_checkpoints/.env")
    load_dotenv(dotenv_path=env_path)
    
    try:
        # Connect to local database first
        local_con = duckdb.connect(db_path)
        
        # Get MotherDuck token from environment
        motherduck_token = os.getenv('MOTHERDUCK_TOKEN')
        if not motherduck_token:
            raise ValueError("MOTHERDUCK_TOKEN not found in .env file")
        
        print("Uploading calendar data to MotherDuck...")
        
        # Attach MotherDuck
        local_con.sql("ATTACH 'md:'")
        print("Connected to MotherDuck")
        
        # Create database in MotherDuck
        local_con.sql("""
            CREATE DATABASE IF NOT EXISTS calendar_data_cloud 
            FROM CURRENT_DATABASE()
        """)
        
        # Connect directly to the new database
        md_con = duckdb.connect('md:calendar_data_cloud')
        
        # Verify the contacts upload
        contacts_stats = md_con.sql("""
            SELECT 
                COUNT(*) as total_contacts,
                COUNT(DISTINCT domain) as unique_domains,
                COUNT(DISTINCT source) as unique_sources,
                MIN(event_time) as earliest_contact,
                MAX(event_time) as latest_contact
            FROM contacts
        """).fetchdf()
        
        print("\nContacts in MotherDuck:")
        print(contacts_stats)
        
        # Verify the events upload
        events_stats = md_con.sql("""
            SELECT 
                COUNT(*) as total_events,
                COUNT(DISTINCT organizer_email) as unique_organizers,
                MIN(start_time) as earliest_event,
                MAX(end_time) as latest_event,
                SUM(CASE WHEN is_recurring THEN 1 ELSE 0 END) as recurring_events,
                AVG(attendee_count) as avg_attendees
            FROM calendar_events
        """).fetchdf()
        
        print("\nEvents in MotherDuck:")
        print(events_stats)
        
        # Show recent events sample
        print("\nRecent Events Sample:")
        recent_events = md_con.sql("""
            SELECT 
                summary,
                start_time,
                organizer_email,
                attendee_count
            FROM calendar_events
            ORDER BY start_time DESC
            LIMIT 5
        """).fetchdf()
        print(recent_events)
        
        print("\nDatabase successfully uploaded to MotherDuck!")
        
        # Close connections
        local_con.close()
        md_con.close()
        
    except Exception as e:
        print(f"Error uploading to MotherDuck: {str(e)}")
        print("Full error details:", e.__class__.__name__)
        return False

if __name__ == "__main__":
    # Fetch and store calendar data locally
    df, events = fetch_calendar_data()
    
    if not df.empty:
        write_contacts_to_duckdb(df)
        
    if events:
        write_events_to_duckdb(events)
    
    # Upload to MotherDuck
    upload_to_motherduck()