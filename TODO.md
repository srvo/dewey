# TODO.md

## Current Priorities
1. Repository Setup & Core Infrastructure
2. Database Integration & Synchronization
3. CRM Module Integration & Execution
4. LLM Integration Foundation

## Human Tasks

### Database Integration (High Priority)
1. [x] Set up MotherDuck cloud instance
   - [x] Create account and configure access
   - [x] Set up API keys and environment variables
   - [x] Test basic connectivity
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

## Import Statements
When importing from dewey modules, use absolute imports:
```python
from dewey.core.architecture import analyze_architecture
from dewey.maintenance import prd_builder
from dewey.core.automation import service_deployment
from dewey.llm.litellm_client import LiteLLMClient  # Preferred over deprecated llm_utils
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
x Implement DuckDB/MotherDuck sync functionality
  - Created DuckDBSync class for bidirectional sync
  - Added auto-sync for modified tables
  - Created command-line sync script
  - Added tests for sync functionality
x Consolidate UI directories
  - Merged src/dewey/ui into src/ui
  - Reorganized components to follow conventions
  - Added proper documentation

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
