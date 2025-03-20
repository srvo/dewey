# TODO.md

## Current Priorities
1. Repository Setup & Core Infrastructure
2. Database Integration & Synchronization
3. CRM Module Integration & Execution
4. LLM Integration Foundation

## Human Tasks

- clarify prd builder invocation -- is there a proper alias in zshrc?

### Database Integration (High Priority)
1. [ ] Set up MotherDuck cloud instance
   - [ ] Create account and configure access
   - [ ] Set up API keys and environment variables
   - [ ] Test basic connectivity
2. [ ] Design and implement core database schema
   - [ ] Create schema migration system
   - [ ] Define table structures and relationships
   - [ ] Set up indexes and partitioning
3. [ ] Develop synchronization system
   - [ ] Create sync status tracking
   - [ ] Implement conflict resolution
   - [ ] Set up cron jobs for regular sync
4. [ ] Implement connection management
   - [ ] Create connection pool
   - [ ] Add fallback mechanisms
   - [ ] Set up health monitoring
5. [ ] Configure backup system
   - [ ] Set up local backup scripts
   - [ ] Configure MotherDuck snapshots
   - [ ] Test restore procedures
6. [ ] Database Optimization
   - [x] Create indexes:
     - [x] unified_emails: (thread_id, created_at) for thread-based queries
     - [x] unified_emails: (from_address, created_at) for sender analysis
     - [x] unified_contacts: (domain, email) for company-based lookups
     - [x] unified_contacts: (last_interaction_date) for activity tracking
     - [x] email_metadata: (email_id) for quick metadata lookups
   - [ ] Add constraints:
     - [ ] Foreign key between email_client_updates.email_id and unified_emails.id
     - [ ] Foreign key between email_metadata.email_id and unified_emails.id
     - [ ] Check constraint on unified_contacts.email for valid email format
     - [ ] Not null constraints on critical fields (thread_id, from_address in unified_emails)
   - [ ] Optimize table statistics:
     - [ ] Regular ANALYZE on unified_emails and unified_contacts
     - [ ] Set up auto-vacuum for large tables
     - [ ] Monitor and adjust table storage parameters

### Email Import System (In Progress)
1. [ ] Historical Email Import
   - [x] Set up IMAP-based import system
   - [x] Implement proper Gmail ID extraction (X-GM-MSGID, X-GM-THRID)
   - [x] Create client communications index view
   - [ ] Monitor import progress (currently importing 2021-2022 emails)
   - [ ] Create progress tracking dashboard
   - [ ] Set up automated monitoring for import process
   - [ ] Document import coverage and gaps

2. [ ] Email Processing Pipeline
   - [ ] Create robust error handling for IMAP timeouts
   - [ ] Implement rate limiting and backoff strategies
   - [ ] Add checkpointing for import progress
   - [ ] Set up email deduplication system
   - [ ] Create email threading visualization
   - [ ] Implement email categorization system

3. [ ] Data Quality Checks
   - [ ] Verify email dates are correctly preserved
   - [ ] Ensure thread IDs are properly linked
   - [ ] Validate client vs system email classification
   - [ ] Check for missing or corrupted content
   - [ ] Monitor storage efficiency

### Test Suite Refinement (High Priority)
1. [ ] Test Infrastructure
   - [ ] Set up test data fixtures
   - [ ] Create mock IMAP server for testing
   - [ ] Implement test database isolation
   - [ ] Add CI/CD pipeline for tests

2. [ ] Test Coverage
   - [ ] Add unit tests for email processing
   - [ ] Create integration tests for IMAP import
   - [ ] Test thread ID extraction and linking
   - [ ] Verify client communication indexing
   - [ ] Test email categorization logic

3. [ ] Test Performance
   - [ ] Benchmark import operations
   - [ ] Profile database queries
   - [ ] Optimize slow tests
   - [ ] Add performance regression tests

4. [ ] Test Maintenance
   - [ ] Clean up obsolete tests
   - [ ] Update test documentation
   - [ ] Standardize test naming conventions
   - [ ] Add test coverage reporting

### Automated Tasks
1. [ ] Regular database maintenance
   - [ ] Vacuum and optimize local database
   - [ ] Update statistics
   - [ ] Monitor disk space
2. [ ] Synchronization monitoring
   - [ ] Track sync status
   - [ ] Alert on failures
   - [ ] Log performance metrics
3. [ ] Backup verification
   - [ ] Verify backup integrity
   - [ ] Test restore procedures
   - [ ] Clean up old backups

### Code Consolidation
1. [ ] Review code_consolidator.py report
2. [ ] Prioritize key clusters for consolidation
3. [ ] Implement canonical versions of clustered functions
4. [ ] Update dependent code to use canonical implementations
5. [ ] Analyze code_consolidator.py report and identify top consolidation opportunities
6. [ ] Reimplement PyPI search with proper API integration
7. [x] Organize orphaned scripts into maintenance directory structure:
   - [x] Move database maintenance scripts:
     - [x] cleanup_tables.py -> src/dewey/maintenance/database/cleanup_tables.py
     - [x] consolidate_schemas.py -> Archived (functionality in BaseMaintenanceScript)
     - [x] cleanup_database.py -> Archived (functionality in BaseMaintenanceScript)
     - [x] check_tables.py -> Archived (functionality in BaseMaintenanceScript)
     - [x] drop_other_tables.py -> Archived (functionality in BaseMaintenanceScript)
     - [x] cleanup_other_tables.py -> Archived (functionality in BaseMaintenanceScript)
   - [x] Move data cleanup scripts:
     - [x] cleanup_small_csvs.py -> Archived
     - [x] cleanup_other_files.py -> Archived
     - [x] migrate_input_data.py -> Archived
   Note: Scripts have been archived and their functionality is now part of the BaseMaintenanceScript class
- [ ] Fix search/replace block in auto_categorize.py (low priority)

### CSV Corpus Classification (High Priority)
1. [ ] Develop classification criteria:
   - [ ] Define data quality metrics
   - [ ] Create relevance scoring system
   - [ ] Establish content categories (financial, gaming, config, etc.)
   - [ ] Set retention/deletion rules for each category

2. [ ] Implement automated classification:
   - [ ] Create script to analyze CSV structure and content
   - [ ] Detect configuration files and game data
   - [ ] Identify personally identifiable information (PII)
   - [ ] Flag low-quality or corrupted data

3. [ ] Data organization:
   - [ ] Create directory structure for categorized data
   - [ ] Move files to appropriate categories
   - [ ] Document classification decisions
   - [ ] Track excluded/deleted files

4. [ ] Quality assurance:
   - [ ] Review auto-classification results
   - [ ] Validate PII detection
   - [ ] Verify data integrity after moves
   - [ ] Update database references

5. [ ] Documentation:
   - [ ] Document classification methodology
   - [ ] Create data catalog
   - [ ] Record excluded data types
   - [ ] Update data pipeline documentation

## Documentation

### PRD Development (High Priority)
1. [ ] Core Module PRD - Data ingestion, processing, analysis
2. [ ] LLM Integration PRD - API clients, rate limiting, model management  
3. [ ] Pipeline Architecture PRD - Read/Resolve/Unify stages
4. [ ] UI Components PRD - Screen hierarchy and data flow
5. [ ] Deployment Strategy PRD - Cloud integration and scaling

### LLM Tasks

#### High Priority
- Ensure various scripts are neatly integrated and well documented

#### Medium Priority
6. LLM helper functions foundation
7. Google Gemini API scaffolding
8. Documentation initialization

### CRM Module
- Refactor database connection and error handling in `add_enrichment_a154a675.py` to use centralized utilities
- Move `src/dewey/core/automation/service_deployment.py` to `src/dewey/core/automation/`

## Import Statements
When importing from dewey modules, use absolute imports:
```python
from dewey.core.architecture import analyze_architecture
from dewey.maintenance import prd_builder
from dewey.core.automation import service_deployment
from dewey.llm import llm_utils
```

For third-party imports, specify version requirements in pyproject.toml:
```python
import click  # For CLI
import yaml   # For config
import rich   # For console output
import typer  # For advanced CLI
```

## Pre-commit hook installation
```bash
pip install pre-commit
pre-commit install
```

## Ruff commands
```bash
uv run ruff check .
uv run ruff format .
```

## Backup procedure
After each successful data processing run:
a. Sync changes to MotherDuck cloud instance
b. Copy the local DuckDB file (dewey.duckdb) to backup location
c. Verify backup integrity
d. Clean up old backups according to retention policy

## Data locations
```bash
Primary Database: md:dewey@motherduck/dewey.duckdb
Local Database: /Users/srvo/dewey/dewey.duckdb
Backup Location: /Users/srvo/dewey/backups/
```

## Pipeline stages
```bash
Read: Read data from source files using Ibis.
Resolve: Merge schemas using DeepInfra API.
Unify: Create target table and insert data.
Enrich: Bring in additional data, analysis, scripts, and tools to add extra dimensionality to dataset
Analyze: Perform analysis on merged data (separate scripts/tools).
```

## Completed Tasks
x Review generated conventions.md
x Ensure Python 3.12 + uv setup
x Decide first core module (Accounting)
x Generate complete `pyproject.toml` with dependencies
x Create core directory structure

# *SEARCH/REPLACE block* Rules:

Every *SEARCH/REPLACE block* must use this format:
1. The *FULL* file path alone on a line, verbatim. No bold asterisks, no quotes around it, no escaping of characters, etc.
2. The opening fence and code language, eg: ````python
3. The start of search block: <<<<<<< SEARCH
4. A contiguous chunk of lines to search for in the existing source code
5. The dividing line: =======
6. The lines to replace into the source code
7. The end of the replace block: >>>>>>> REPLACE
8. The closing fence: ```

Use the *FULL* file path, as shown to you by the user.

Every *SEARCH* section must *EXACTLY MATCH* the existing file content, character for character, including all comments, docstrings, etc.
If the file contains code or other data wrapped/escaped in json/xml/quotes or other containers, you need to propose edits to the literal contents of the file, including the container markup.

*SEARCH/REPLACE* blocks will *only* replace the first match occurrence.
Including multiple unique *SEARCH/REPLACE* blocks if needed.
Include enough lines in each SEARCH section to uniquely match each set of lines that need to change.

Keep *SEARCH/REPLACE* blocks concise.
Break large *SEARCH/REPLACE* blocks into a series of smaller blocks that each change a small portion of the file.
Include just the changing lines, and a few surrounding lines if needed for uniqueness.
Do not include long runs of unchanging lines in *SEARCH/REPLACE* blocks.

Only create *SEARCH/REPLACE* blocks for files that the user has added to the chat!

To move code within a file, use 2 *SEARCH/REPLACE* blocks: 1 to delete it from its current location, 1 to insert it in the new location.

Pay attention to which filenames the user wants you to edit, especially if they are asking you to create a new file.

If you want to put code in a new file, use a *SEARCH/REPLACE block* with:
- A new file path, including dir name if needed
- An empty `SEARCH` section
- The new file's contents in the `REPLACE` section

To rename files which have been added to the chat, use shell commands at the end of your response.

If the user just says something like "ok" or "go ahead" or "do that" they probably want you to make SEARCH/REPLACE blocks for the code changes you just proposed.
The user will say when they've applied your edits. If they haven't explicitly confirmed the edits have been applied, they probably want proper SEARCH/REPLACE blocks.


ONLY EVER RETURN CODE IN A *SEARCH/REPLACE BLOCK*!

Examples of when to suggest shell commands:

- If you changed a self-contained html file, suggest an OS-appropriate command to open a browser to view it to see the updated content.
- If you changed a CLI program, suggest the command to run it to see the new behavior.
- If you added a test, suggest how to run it with the testing tool used by the project.
- Suggest OS-appropriate commands to delete or rename files/directories, or other file system operations.
- If your code changes add new dependencies, suggest the command to install them.
- Etc.
