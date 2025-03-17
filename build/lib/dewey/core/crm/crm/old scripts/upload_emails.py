import duckdb
import pandas as pd
from supabase import create_client
from pathlib import Path
import time
from typing import List, Dict, Any

# Supabase setup
supabase_url = "https://fjzxtsewrykbrfjzatti.supabase.co"
supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZqenh0c2V3cnlrYnJmanphdHRpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzE3NDE0ODUsImV4cCI6MjA0NzMxNzQ4NX0.faaMQ6bwUHdf5c0SjqUZ7Unr7JW8PtAb_-mG1V9Iang"

def upload_batch(supabase, emails: List[Dict[str, Any]], retry_count: int = 3) -> bool:
    """Upload a batch of emails with retries"""
    for attempt in range(retry_count):
        try:
            result = supabase.table('Emails').insert(emails).execute()
            print(f"Successfully uploaded {len(emails)} emails")
            return True
        except Exception as e:
            if attempt == retry_count - 1:
                print(f"Failed to upload batch after {retry_count} attempts: {str(e)}")
                return False
            print(f"Attempt {attempt + 1} failed, retrying...")
            time.sleep(2 ** attempt)  # Exponential backoff
    return False

def upload_emails():
    try:
        # Connect to Supabase
        supabase = create_client(supabase_url, supabase_key)
        print("Connected to Supabase")

        # Connect to DuckDB
        con = duckdb.connect("/Users/srvo/lc/data/crm/emails/emails.duckdb")
        print("Connected to DuckDB")

        # Process in smaller batches
        batch_size = 50  # Reduced from 100
        offset = 0
        total_processed = 0
        failed_batches = 0

        while True:
            query = f"""
            SELECT 
                from_name,
                from_email,
                subject,
                date as sent_date,
                is_mailing_list,
                to_address,
                body_preview as body,
                thread_id
            FROM emails
            LIMIT {batch_size} OFFSET {offset}
            """
            
            df = con.execute(query).fetchdf()
            if len(df) == 0:
                break

            # Process emails
            emails_batch = []
            for _, email in df.iterrows():
                email_data = {
                    'subject': email.subject if pd.notna(email.subject) else "",
                    'body': email.body if pd.notna(email.body) else "",
                    'sent_date': email.sent_date.isoformat() if pd.notna(email.sent_date) else None,
                    'from_address': f"{email.from_name} <{email.from_email}>" if pd.notna(email.from_email) else "",
                    'to_addresses': [email.to_address] if pd.notna(email.to_address) else [],
                    'thread_id': email.thread_id if pd.notna(email.thread_id) else None,
                    'labels': ['mailing_list'] if email.is_mailing_list else []
                }
                emails_batch.append(email_data)

            # Upload batch with retries
            if upload_batch(supabase, emails_batch):
                total_processed += len(emails_batch)
            else:
                failed_batches += 1

            print(f"Processed {total_processed} emails (Failed batches: {failed_batches})")
            offset += batch_size
            time.sleep(0.5)  # Rate limiting

        print(f"\nEmail upload complete!")
        print(f"Total processed: {total_processed}")
        print(f"Failed batches: {failed_batches}")

    except Exception as e:
        print(f"Error uploading emails: {str(e)}")
    finally:
        con.close()

if __name__ == "__main__":
    upload_emails() 