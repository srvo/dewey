import argparse
import logging
import os
from datetime import datetime
from typing import List

import pandas as pd
from sqlalchemy import create_engine, inspect, func
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from schema import Base, AttioContact, OnyxEnrichment

def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

def get_db_connection():
    load_dotenv()
    db_url = os.getenv("DB_URL")
    if not db_url:
        raise ValueError(
            "DB_URL environment variable not set\n"
            "1. Confirm.env file exists in current directory\n"
            "2. Verify it contains: DB_URL=postgresql://user:pass@host/dbname"
        )
    return create_engine(db_url)

def export_table_to_csv(engine, model, output_file: str) -> int:
    """Export database table to CSV using pandas for better type handling."""
    with engine.connect() as conn:
        df = pd.read_sql_table(model.__tablename__, conn)
        if not df.empty:
            df.to_csv(output_file, index=False)
            return len(df)
        return 0

def get_table_stats(engine):
    """Get basic table statistics."""
    inspector = inspect(engine)
    stats = {}
    
    with engine.connect() as conn:
        for table_name in inspector.get_table_names():
            stats[table_name] = {
                'total_records': conn.execute(f"SELECT COUNT(*) FROM {table_name}").scalar(),
                'columns': inspector.get_columns(table_name)
            }
    return stats

def add_contact_insights(session):
    """Generate business insights from contact data."""
    insights = {}
    
    # Total contacts
    insights['total_contacts'] = session.query(AttioContact).count()
    
    # Email domain analysis
    email_domains = session.query(
        func.substring(
            AttioContact.email_addresses,
            func.strpos(AttioContact.email_addresses, '@') + 1
        ).label('domain'),
        func.count().label('count')
    ).group_by('domain').order_by(func.count().desc()).limit(5).all()
    
    insights['top_domains'] = dict(email_domains)
    
    # Missing last email date analysis
    insights['missing_last_email'] = session.query(AttioContact).filter(
        AttioContact.last_email_interaction_when == '1970-01-01'
    ).count()
    
    return insights

def main():
    configure_logging()
    logger = logging.getLogger(__name__)
    
    try:
        engine = get_db_connection()
        inspector = inspect(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results = []

        # Get statistics
        stats = get_table_stats(engine)
        contact_insights = add_contact_insights(session)
        
        # Print summary
        logger.info("\nDatabase Summary:")
        for table, data in stats.items():
            logger.info(f"{table}: {data['total_records']} records")
            logger.info(f"Columns: {[c['name'] for c in data['columns']]}")
        
        logger.info("\nContact Insights:")
        logger.info(f"Total contacts: {contact_insights['total_contacts']}")
        logger.info(f"Contacts missing email date: {contact_insights['missing_last_email']}")
        logger.info("Top email domains:")
        for domain, count in contact_insights['top_domains'].items():
            logger.info(f"  {domain}: {count}")

        # Existing export functionality
        for model, name in [(AttioContact, "contacts"), (OnyxEnrichment, "enrichments")]:
            filename = f"db_export_{name}_{timestamp}.csv"
            count = export_table_to_csv(engine, model, filename)
            results.append(f"Exported {count} {name} to {filename}")

        logger.info("\nExport Summary:\n" + "\n".join(f"• {r}" for r in results))

    except Exception as e:
        logger.error(f"Operation failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()
