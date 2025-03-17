# CRM System



## Executive Summary

{'executive_summary': {'overview': 'This document outlines the product requirements for a CRM system focused on email processing and contact enrichment. The system aims to automate email-related tasks, extract valuable information from email content, and enrich contact data from various sources.', 'architecture': 'The architecture is component-based, with modules responsible for specific tasks such as email classification, contact enrichment, and data ingestion. The system leverages various libraries and APIs for email processing (Gmail API), data storage (SQL databases), and external enrichment services (Attio, Onyx). No specific architectural patterns are explicitly defined in the provided data.', 'components': 'Key components include: (1) Email processing modules (gmail/*) for fetching and parsing emails. (2) Enrichment modules (enrichment/*) for extracting contact information and detecting opportunities. (3) Classification modules (email_classifier/*) for prioritizing emails. (4) Data management modules (csv_ingestor.py, event_manager.py) for importing data and managing events. (5) Action management (action_manager_fff42dfb_1.py) for executing email-related actions. Interactions between components involve data flow from email processing to enrichment and classification, with results stored in databases.', 'issues': 'The provided data does not explicitly list critical issues. However, potential issues include: (1) Scalability of email processing and enrichment. (2) Reliability of external API integrations. (3) Data quality and accuracy of extracted information. (4) Handling of diverse email formats and content. Mitigation strategies should include robust error handling, retry mechanisms, and data validation.', 'next_steps': 'Next steps include: (1) Defining clear architectural patterns for scalability and maintainability. (2) Implementing comprehensive testing and monitoring. (3) Addressing potential security vulnerabilities. (4) Establishing data governance policies. (5) Further defining the interactions between the components to ensure a smooth workflow.'}}

## Components

### list_person_records.py

No description available.

#### Responsibilities


#### Dependencies

- requests library

### md_schema.py

No description available.

#### Responsibilities

- Provide statistics
- Execute the main program logic
- Parse markdown file
- Return structured schema

#### Dependencies

- argparse library

### action_manager_fff42dfb_1.py

Action Manager Module.

This module provides functionality for executing various email-related actions based on
defined rules and email data. It serves as the central point for managing all email
processing actions within the system.

Key Features:
- Action execution with comprehensive logging
- Error handling and reporting
- Future extensibility for new action types

The module is designed to be integrated with the email processing pipeline and works
in conjunction with the rules engine to determine appropriate actions for each email.

#### Responsibilities

- Execute an action on an email based on provided data and rules.

#### Dependencies

- log_config library

### csv_ingestor.py

No description available.

#### Responsibilities

- Validate CSV rows.
- Ingest CSV data from a file.
- Map CSV rows to AttioContact instances.

#### Dependencies

- sqlalchemy library
- argparse library
- time library
- db library
- dotenv library
- csv library

### csv_schema_infer.py

No description available.

#### Responsibilities

- Infer schema from a CSV file.
- Format the schema output.
- Determine if a value is a float.
- Execute the main program logic.
- Determine if a value is boolean.
- Determine if a value is a datetime.
- Determine if a value is an integer.

#### Dependencies

- datetime library
- collections library
- argparse library
- csv library

### event_manager.py

No description available.

#### Responsibilities

- Return the number of stored events
- Enrich events with email information
- Log an error message
- Create and store a new event
- Log an exception message
- Retry operations
- Enrich events with contact information
- Retry a function call if an exception occurs
- Return an iterator for stored events
- Log an informational message
- Return all stored event objects
- Persist events to storage
- Set contextual data for subsequent events
- Manage event creation and storage
- Initialize EventManager with request ID and retry attempts
- Filter stored events based on criteria
- Return all stored events
- Filter and retrieve events

#### Dependencies

- time library
- dataclasses library
- load_config.py for config functionality

### transcript_matching.py

No description available.

#### Responsibilities

- Match transcript files based on naming conventions.

#### Dependencies

- pathlib library
- re library
- difflib library
- sqlite3 library

### email_classifier/process_feedback.py

Initialize database connection and create tables if needed

#### Responsibilities

- Generate feedback in JSON format
- Save feedback data
- Update user preferences
- Load user preferences
- Load feedback data
- Initialize the database
- Execute the main program logic
- Suggest changes to rules
- Save user preferences

#### Dependencies

- time library
- src library
- collections library

### email_classifier/email_classifier.py

Email classifier for Gmail using Deepinfra API for prioritization.

#### Responsibilities

- Load email preferences from a JSON file
- Apply the priority label
- Create or get a label ID
- Store analysis results in DuckDB
- Execute the main program logic
- Extract attachment information from message parts
- Get a DuckDB connection
- Save the feedback file
- Create draft in Gmail and apply review label
- Authenticate with the Gmail API
- Initialize a feedback entry in feedback.json
- Scan message parts
- Calculate uncertainty of scores
- Retrieve the full message body
- Retrieve critical priority emails from database
- Generate draft response using Hermes-3-Llama-3.1-405B model
- Extract a part from a message
- Analyze email content using the DeepInfra API
- Calculate email priority
- Recursively extract message parts from payload

#### Dependencies

- datetime library
- argparse library
- google_auth_oauthlib library
- duckdb library
- openai library
- requests library
- time library
- base64 library
- googleapiclient library
- dotenv library
- google library

### enrichment/opportunity_detection.py

Script to detect business opportunities from email content.

Dependencies:
- SQLite database with processed contacts
- Regex for opportunity detection
- pandas for data manipulation

#### Responsibilities

- Update contacts database
- Detect opportunities
- Extract opportunities

#### Dependencies

- re library
- src library
- pandas library
- config library
- sqlite3 library

### enrichment/contact_enrichment.py

Contact Enrichment System with Task Tracking and Multiple Data Sources.

This module provides comprehensive contact enrichment capabilities by:
- Extracting contact information from email signatures and content
- Managing enrichment tasks with status tracking
- Storing enrichment results with confidence scoring
- Integrating with multiple data sources
- Providing detailed logging and error handling

The system is designed to be:
- Scalable: Processes emails in batches with configurable size
- Reliable: Implements task tracking and retry mechanisms
- Extensible: Supports adding new data sources and extraction patterns
- Auditable: Maintains detailed logs and task history

Key Features:
- Regex-based contact information extraction
- Task management system with status tracking
- Confidence scoring for extracted data
- Source versioning and validation
- Comprehensive logging and error handling

#### Responsibilities

- Extract contact information from email message text using regex patterns.
- Store enrichment data from a specific source with version control.
- Update the status and details of an enrichment task.
- Create a new enrichment task in the database.
- Process a batch of emails for contact enrichment.
- Process a single email for contact enrichment.

#### Dependencies

- re library
- src library
- __future__ library
- uuid library
- config library
- scripts library

### enrichment/attio_onyx_enrichment_engine.py

Core enrichment workflow coordinating Attio and Onyx integrations.

#### Responsibilities

- Process contact data
- Store enrichment results
- Orchestrate contact enrichment
- Store the enriched contact data
- Process individual contact data
- Save data to a PostgreSQL database
- Initialize the EnrichmentEngine
- Execute the contact enrichment process

#### Dependencies

- datetime library
- sqlalchemy library
- api_clients library
- schema library

### enrichment/add_enrichment.py

Add enrichment capabilities to existing database while preserving sync functionality.

This module provides functionality to enhance the existing database with data enrichment
capabilities. It adds new tables and columns to support:
- Contact enrichment tracking
- Task management for enrichment processes
- Source tracking for enriched data
- Confidence scoring and status tracking

The changes are designed to be non-destructive and maintain compatibility with existing
database operations.

#### Responsibilities

- Add columns to the contacts table for enrichment tracking
- Create enrichment_tasks table
- Create enrichment_sources table

#### Dependencies

- scripts library
- sqlite3 library

### enrichment/email_enrichment_service.py

Service for enriching email metadata.

#### Responsibilities

- Extract plain and HTML message bodies.
- Calculate and assign a priority score to emails.
- Enrich emails with message body content.
- Extract message bodies from email data.
- Enrich an email with message body and priority score.

#### Dependencies

- structlog library
- django library
- gmail_history_sync library
- __future__ library
- prioritization library
- base64 library
- database library

### gmail/models.py

No description available.

#### Responsibilities

- Represent a raw email message
- Store raw email data

#### Dependencies

- datetime library

### gmail/email_processor.py

No description available.

#### Responsibilities

- Parse email date strings into timezone-aware datetime objects
- Parse email addresses
- Process a single email message
- Parse email addresses from a header value
- Process email messages
- Decode base64-encoded email body content
- Extract relevant information from emails
- Extract and decode message body from Gmail API payload

#### Dependencies

- datetime library
- uuid library
- zoneinfo library
- base64 library
- email library

### gmail/gmail_client.py

No description available.

#### Responsibilities

- Decode the message body from base64.
- Authenticate with Gmail API using a service account.
- Authenticate with the Gmail API.
- Fetch emails from Gmail based on the provided query.
- Initialize the Gmail client with service account credentials.
- Retrieve a specific email message by ID.
- Fetch emails from Gmail based on a query.

#### Dependencies

- pathlib library
- base64 library
- googleapiclient library
- google library

### gmail/email_service.py

No description available.

#### Responsibilities

- Initializes the EmailService.
- Sets up signal handlers.
- Handles graceful shutdown.
- Runs the email service continuously.
- Handles shutdown signals.
- Fetches and processes emails.
- Manages email fetching and processing.
- Runs the email service in a loop.

#### Dependencies

- time library
- signal library
- datetime library

### gmail/gmail_sync.py

No description available.

#### Responsibilities

- Performs an initial synchronization of Gmail messages.
- Performs an incremental synchronization of Gmail messages.
- Performs initial synchronization of Gmail messages based on a query.
- Performs incremental synchronization of Gmail messages using the History API.
- Initializes Gmail synchronization with a GmailClient.
- Initializes the GmailSync class with a GmailClient instance.

#### Dependencies

- googleapiclient library

## Architectural Decisions

