"""Database models and schemas for the Dewey project.

This module provides SQL schemas and table definitions for the Dewey project.
"""

# Email analysis table schema
EMAIL_ANALYSES_SCHEMA = """
CREATE TABLE IF NOT EXISTS email_analyses (
    msg_id VARCHAR PRIMARY KEY,
    thread_id VARCHAR,
    subject VARCHAR,
    from_address VARCHAR,
    analysis_date TIMESTAMP,
    raw_analysis JSON,
    automation_score FLOAT,
    content_value FLOAT,
    human_interaction FLOAT,
    time_value FLOAT,
    business_impact FLOAT,
    uncertainty_score FLOAT,
    metadata JSON,
    priority INTEGER,
    label_ids JSON,
    snippet TEXT,
    internal_date BIGINT,
    size_estimate INTEGER,
    message_parts JSON,
    draft_id VARCHAR,
    draft_message JSON,
    attachments JSON
)
"""

# Contacts table schema
CONTACTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY,
    name VARCHAR,
    email VARCHAR UNIQUE,
    company VARCHAR,
    title VARCHAR,
    phone VARCHAR,
    linkedin VARCHAR,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP,
    notes TEXT,
    metadata JSON
)
"""

# Email labels table schema
EMAIL_LABELS_SCHEMA = """
CREATE TABLE IF NOT EXISTS email_labels (
    id INTEGER PRIMARY KEY,
    email_id VARCHAR,
    label VARCHAR,
    FOREIGN KEY (email_id) REFERENCES email_analyses(msg_id)
)
"""

# Create index statements
EMAIL_ANALYSES_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_email_analyses_thread_id ON email_analyses(thread_id)",
    "CREATE INDEX IF NOT EXISTS idx_email_analyses_from_address ON email_analyses(from_address)",
    "CREATE INDEX IF NOT EXISTS idx_email_analyses_internal_date ON email_analyses(internal_date)"
]

CONTACTS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email)",
    "CREATE INDEX IF NOT EXISTS idx_contacts_company ON contacts(company)"
]

EMAIL_LABELS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_email_labels_email_id ON email_labels(email_id)",
    "CREATE INDEX IF NOT EXISTS idx_email_labels_label ON email_labels(label)"
]

# Dictionary mapping table names to their schemas
TABLE_SCHEMAS = {
    "email_analyses": EMAIL_ANALYSES_SCHEMA,
    "contacts": CONTACTS_SCHEMA,
    "email_labels": EMAIL_LABELS_SCHEMA
}

# Dictionary mapping table names to their indexes
TABLE_INDEXES = {
    "email_analyses": EMAIL_ANALYSES_INDEXES,
    "contacts": CONTACTS_INDEXES,
    "email_labels": EMAIL_LABELS_INDEXES
} 