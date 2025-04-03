#!/usr/bin/env python3
"""Utility functions for checking Gmail data in MotherDuck."""

import json
import logging
from src.dewey.core.db.connection import get_motherduck_connection

logger = logging.getLogger(__name__)

def check_email_count():
    """Get total count of emails in the database."""
    try:
        with get_motherduck_connection() as conn:
            result = conn.execute('SELECT COUNT(*) FROM emails').fetchall()
            return result[0][0]
    except Exception as e:
        logger.error(f"Error connecting to MotherDuck: {e}")
        return None

def check_email_schema():
    """Get the schema of the emails table."""
    try:
        with get_motherduck_connection() as conn:
            schema = conn.execute('PRAGMA table_info(emails)').fetchall()
            return [(col[1], col[2]) for col in schema]
    except Exception as e:
        logger.error(f"Error querying MotherDuck: {e}")
        return None

def check_email_content(limit=10):
    """Check email content including metadata and body."""
    try:
        with get_motherduck_connection() as conn:
            samples = conn.execute(
                'SELECT msg_id, metadata, snippet FROM emails LIMIT ?', 
                [limit]
            ).fetchall()
            
            results = []
            for sample in samples:
                msg_id, metadata_json, snippet = sample
                content = {
                    'msg_id': msg_id,
                    'snippet': snippet,
                    'metadata': json.loads(metadata_json) if metadata_json else None
                }
                results.append(content)
            return results
    except Exception as e:
        logger.error(f"Error querying email content: {e}")
        return None

def check_enrichment_status(limit=10):
    """Check email enrichment status."""
    try:
        with get_motherduck_connection() as conn:
            exists = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='email_enrichment_status'"
            ).fetchone()
            
            if not exists:
                return {'error': 'Table email_enrichment_status does not exist'}
            
            count = conn.execute(
                "SELECT COUNT(*) FROM email_enrichment_status"
            ).fetchone()[0]
            
            samples = conn.execute("""
                SELECT s.email_id, s.status, s.priority_score, s.priority_reason, 
                       e.subject, e.from_address
                FROM email_enrichment_status s
                JOIN emails e ON s.email_id = e.msg_id
                LIMIT ?
            """, [limit]).fetchall()
            
            return {
                'total_count': count,
                'samples': [
                    {
                        'email_id': s[0],
                        'status': s[1],
                        'priority_score': s[2],
                        'priority_reason': s[3],
                        'subject': s[4],
                        'from_address': s[5]
                    }
                    for s in samples
                ]
            }
    except Exception as e:
        logger.error(f"Error checking enrichment status: {e}")
        return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("Checking email count...")
    count = check_email_count()
    print(f"Total emails: {count}")
    
    print("\nChecking email schema...")
    schema = check_email_schema()
    if schema:
        for col_name, col_type in schema:
            print(f"  {col_name} ({col_type})")
    
    print("\nChecking email content...")
    content = check_email_content(limit=5)
    if content:
        for i, email in enumerate(content, 1):
            print(f"\nEmail {i}:")
            print(f"  ID: {email['msg_id']}")
            print(f"  Snippet: {email['snippet'][:60]}...")
            if email['metadata']:
                print(f"  Metadata keys: {', '.join(email['metadata'].keys())}")
    
    print("\nChecking enrichment status...")
    status = check_enrichment_status(limit=5)
    if status and 'samples' in status:
        print(f"Total enriched emails: {status['total_count']}")
        for i, sample in enumerate(status['samples'], 1):
            print(f"\nEnriched Email {i}:")
            print(f"  ID: {sample['email_id']}")
            print(f"  Status: {sample['status']}")
            print(f"  Priority: {sample['priority_score']}")
            print(f"  Subject: {sample['subject']}")