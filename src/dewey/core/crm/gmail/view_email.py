#!/usr/bin/env python3
"""
Email Viewer Script
==================

This script allows viewing emails stored in the DuckDB database.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

import duckdb

def get_db_connection(db_path: str) -> duckdb.DuckDBPyConnection:
    """Get a DuckDB connection.
    
    Args:
        db_path: Path to the database file
        
    Returns:
        A DuckDB connection
    """
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        sys.exit(1)
    
    # Connect to the database
    return duckdb.connect(db_path)

def list_emails(conn: duckdb.DuckDBPyConnection, limit: int = 10) -> None:
    """List emails in the database.
    
    Args:
        conn: DuckDB connection
        limit: Maximum number of emails to list
    """
    try:
        # Get emails
        result = conn.execute(f"""
        SELECT id, from_email, to_email, subject, date
        FROM emails
        ORDER BY date DESC
        LIMIT {limit}
        """).fetchall()
        
        if not result:
            print("No emails found in the database.")
            return
            
        # Print emails
        print(f"Found {len(result)} emails:")
        print("-" * 80)
        for i, (email_id, from_email, to_email, subject, date) in enumerate(result, 1):
            print(f"{i}. ID: {email_id}")
            print(f"   From: {from_email}")
            print(f"   To: {to_email}")
            print(f"   Subject: {subject}")
            print(f"   Date: {date}")
            print("-" * 80)
            
    except Exception as e:
        print(f"Error listing emails: {e}")
        sys.exit(1)

def view_email(conn: duckdb.DuckDBPyConnection, email_id: str) -> None:
    """View a single email.
    
    Args:
        conn: DuckDB connection
        email_id: Email ID to view
    """
    try:
        # Get email
        result = conn.execute(f"""
        SELECT from_email, to_email, cc_email, bcc_email, subject, date, body, attachments
        FROM emails
        WHERE id = '{email_id}'
        """).fetchone()
        
        if not result:
            print(f"Email with ID {email_id} not found.")
            return
            
        # Unpack result
        from_email, to_email, cc_email, bcc_email, subject, date, body, attachments = result
        
        # Print email
        print("=" * 80)
        print(f"Email ID: {email_id}")
        print(f"Date: {date}")
        print(f"From: {from_email}")
        print(f"To: {to_email}")
        
        if cc_email:
            print(f"CC: {cc_email}")
            
        if bcc_email:
            print(f"BCC: {bcc_email}")
            
        print(f"Subject: {subject}")
        print("=" * 80)
        print("Body:")
        print(body[:2000] + "..." if len(body) > 2000 else body)
        print("=" * 80)
        
        # Print attachments
        if attachments:
            try:
                attachments_list = json.loads(attachments)
                if attachments_list:
                    print("Attachments:")
                    for i, attachment in enumerate(attachments_list, 1):
                        print(f"{i}. {attachment.get('filename')} ({attachment.get('mimeType')})")
            except:
                print(f"Attachments: {attachments}")
                
    except Exception as e:
        print(f"Error viewing email: {e}")
        sys.exit(1)

def main():
    """Run the email viewer."""
    parser = argparse.ArgumentParser(description="View emails from the database")
    parser.add_argument("--db-path", type=str, default="~/dewey_emails.duckdb", 
                        help="Path to the database file")
    parser.add_argument("--list", action="store_true", help="List emails")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of emails to list")
    parser.add_argument("--view", type=str, help="View email with the specified ID")
    
    args = parser.parse_args()
    
    # Expand the database path
    db_path = os.path.expanduser(args.db_path)
    
    # Get database connection
    conn = get_db_connection(db_path)
    
    # List or view emails
    if args.view:
        view_email(conn, args.view)
    else:
        list_emails(conn, args.limit)

if __name__ == "__main__":
    main() 