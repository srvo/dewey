# .aider.conf - Coding Conventions for dewey Project

# Dewey Project Conventions

This document outlines the conventions and standards for the Dewey project codebase.

## Directory Structure

The codebase follows a modular structure:

```
/src
  /core               # Core functionality 
    /accounting       # Accounting-related modules
    /bookkeeping      # Bookkeeping features
    /crm              # Customer relationship management
    /research         # Research and analysis features
    /personal         # Personal user features
    /automation       # Automation workflows
    /engines          # Integration engines
    /migrations       # Migration scripts
    base_script.py    # Base class for all scripts
  
  /llm                # Language model integration
    /agents           # AI agents
    /api_clients      # LLM API clients
    /prompts          # Prompt templates
  
  /ui                 # User interface components
    /screens          # Screen views
    /components       # Reusable UI components
  
  /pipeline           # Data processing pipelines
  
  /utils              # Utility functions and helpers
  
  /tests              # Test modules
```

## Script Development

### BaseScript Usage

All script files should inherit from the `BaseScript` class, which provides consistent structure, logging, and error handling:

```python
from src.core.base_script import BaseScript

class MyScript(BaseScript):
    def run(self):
        # Your implementation here
        self.logger.info("Running my script")
```

### Script Placement

1. Place scripts in the appropriate module directory based on functionality
2. Use clear, descriptive file names
3. If a script handles a specific entity, include that entity in the filename

## Coding Standards

### Python Version

- Use Python 3.9+ features
- Format code with Black (line length 88)
- Use type hints for all function parameters and return values

### Imports

- Group imports in the following order:
  1. Standard library imports
  2. Third-party library imports
  3. Local application imports
- Sort imports alphabetically within each group
- Use absolute imports for clarity

```python
# Standard library
import os
import sys
from typing import Dict, List, Optional

# Third-party libraries
import numpy as np
import pandas as pd

# Local imports
from src.core.base_script import BaseScript
from src.utils.common import get_config
```

### Naming Conventions

- `snake_case` for variables, functions, and methods
- `PascalCase` for classes and types
- `UPPER_CASE` for constants
- Prefix private methods/variables with underscore (`_method_name`)

### Documentation

- All modules, classes, and functions should have docstrings
- Use Google-style docstrings format
- Include examples in docstrings for complex functions

```python
def calculate_metric(data: List[float], window_size: int = 5) -> float:
    """Calculate a rolling metric on the data.
    
    Args:
        data: List of numerical values to process
        window_size: Size of the rolling window
        
    Returns:
        Calculated metric value
        
    Examples:
        >>> calculate_metric([1, 2, 3, 4, 5], window_size=3)
        3.0
    """
    # Implementation...
```

### Error Handling

- Use explicit exception types rather than catching all exceptions
- Log exceptions with appropriate context
- Use context managers for resource handling

### Testing

- Write unit tests for all public functions
- Use pytest as the testing framework
- Aim for high test coverage, especially for critical paths

## Configuration Management

- Store configuration in `dewey.yaml`
- Use environment variables for sensitive data
- Create example configuration files for documentation

## Logging

- Use the logging provided by `BaseScript`
- Include appropriate context in log messages
- Use the correct log level:
  - DEBUG: Detailed debugging information
  - INFO: Confirmation that things are working as expected
  - WARNING: Indication that something unexpected happened
  - ERROR: Due to a more serious problem, the software hasn't been able to perform a function
  - CRITICAL: A serious error, indicating that the program itself may be unable to continue running

## Version Control

- Write clear, concise commit messages
- Use feature branches for development
- Squash commits before merging to main/master

## Dependencies

- Use `uv` for package management and pip functions
- Document dependencies in `pyproject.toml`
- Minimize external dependencies, especially for critical components

All documentation, docstrings, and so forth must be written in english. 

## Centralized Configuration Architecture

### Config File Locations
- **Primary config path:** `/Users/srvo/dewey/config/dewey.yaml`
- Environment-specific overrides: `config/${ENVIRONMENT}_overrides.yaml` 
- All paths in config files are relative to project root (`/Users/srvo/dewey`)
- Secrets must be stored in `.env` at project root

All system configuration MUST be defined in `config/dewey.yaml` using this structure:
- Core system settings under `core`
- Vector store configurations under `vector_stores`
- LLM provider settings under `llm` 
- Pipeline configurations under `pipeline`
- PRD-specific settings under `prd`
- Formatting rules under `formatting`

### Key Rules:
1. No module-specific YAML files allowed (except script_checkpoints.yaml)
2. Cross-module dependencies must reference the central config
3. Environment variables should be used via ${VAR_NAME} syntax
4. Config sections should validate themselves on load
5. script_checkpoints.yaml should only contain transient file hashes
6. Shared config values used by scripts must live in dewey.yaml

**PRD Authoring Standards**

1. Location and Tracking:
   - PRDs must be stored in the `docs` directory within their respective module/target directory
   - Use standardized naming: `[DirectoryName]_Product_Requirements_Document.{yaml|md}`
   - All PRDs must be tracked in `config/dewey.yaml` under `prd.tracked_prds`
   - Both YAML and Markdown versions must be maintained
   - Ensure all components in PRD have complete descriptions
   - All components must have complete descriptions
   
2. Structure:
   - Use YAML format with Markdown sections
   - Follow template from config/dewey.yaml
   - Maintain version history in header
   
3. Stakeholder Handling:
   - Default to Sloane Ortel for non-client modules
   - Auto-include legal/compliance stakeholders for financial modules
   - Track stakeholder review dates

4. Requirements:
   - Categorize as Functional/Technical/Compliance
   - Link to implementation code
   - Include complexity metrics
   
5. Anti-Pattern Avoidance:
   - Validate requirements with LLM before inclusion
   - Auto-generate dependency graphs
   - Enforce timeline realism via historical velocity data

## Consolidated Function Process
0. Identify candidate scripts using hash-suffix pattern (_xxxxxxxx.py)
1. New consolidated functions go in `/consolidated_functions`
2. Run `prd relocate` to:
   - Classify functionality with LLM
   - Move to appropriate module directory
   - Update module PRD documentation
   - Remove duplicates
3. PRD files are maintained in `/docs/prds/[module]_prd.md`

## Maintenance Principles
- Keep TODO.md updated as the single source of truth for tasks with:
  - Clear current priorities ranked by importance
  - Detailed human and automated tasks
  - Completed tasks preserved for historical reference
  - Regular updates (weekly or per milestone)
- Maintain shell aliases in ~/.zshrc for core functions:
  - Version-controlled aliases matching current script locations
  - Simple verbs mapping to complex commands (e.g. `consolidate`, `prd`)
  - Automatic updates when script paths/configs change
- Document architectural decisions in docs/decisions.md
- Synchronize config relationships:
  - script_checkpoints.yaml should reference configs from dewey.yaml
  - Maintain separation due to size differences
  - Shared values extracted to dewey.yaml where possible

## Core Development Guidelines

### Mandatory Base Script Framework
**STRICTLY ENFORCED** - All non-test scripts MUST use:
```python
from dewey.core.base_script import BaseScript

class CustomScript(BaseScript):
    def __init__(self):
        super().__init__(config_section='custom')
        
    def run(self):
        # Implement script logic here
```

**Enforcement Rules:**
1. Absolute requirement for all production code
2. Zero exceptions except temporary code in `/sandbox` (must be moved within 7 days)
3. Violations will:
   - Fail CI/CD pipelines
   - Block PR merges
   - Trigger mandatory code reviews
4. Required inherited functionality:
   - Centralized configuration
   - Standardized logging
   - Connection pooling
   - Error handling framework

**Implementation Rules:**
       def __init__(self):
           super().__init__(
               config_section='custom',
               requires_db=True,
               enable_llm=True
           )

       def run(self):
           # Implementation using self.logger, self.config, etc
   ```
   - Must implement run() method
   - Must use built-in logging (self.logger)
   - Must load configuration through base class
   - Must handle errors through base class mechanisms

3. **Prohibited Patterns:**
   - Standalone scripts without base inheritance
   - Direct config/logging initialization
   - Custom exception handling outside base framework
   - Database connections not using base class pool

**Exceptions:**
- Test scripts in `tests/` directory are exempt from this requirement
- CLI entrypoints may use `if __name__ == "__main__"` patterns as long as they wrap a BaseScript instance

### Agent & Tool Configuration
1. **Engine Integration:**
   - All engines must inherit from `BaseEngine`/`SearchEngine`
   - Tool metadata is automatically generated from method signatures
   - Use `@engine_tool` decorator for config-based tool creation
   - Tools follow naming convention: `{EngineName}_{MethodName}`

2. **Configuration Rules:**
   ```yaml
   engines:
     search_engine:
       class: dewey.core.engines.base.SearchEngine
       enabled: true
   ```yaml
   engines:
     brave_search:
       class: dewey.core.engines.brave.BraveSearchEngine
       enabled: true
       methods: ["search", "news_search"]
       params:
         api_key: ${BRAVE_API_KEY}
         max_results: 15
   ```
   - Engine classes must be fully qualified Python paths
   - Disabled engines remain in config but aren't initialized
   - Methods list specifies which engine methods become tools

3. **Tool Requirements:**
   - Methods must have type annotations for parameters/returns
   - Docstrings become tool descriptions
   - Parameter descriptions default to "Parameter {name} for {method}"
   - Complex types must be JSON-serializable

4. **Error Handling:**
   - Tools automatically validate parameters
   - Type coercion attempts for annotated parameters
   - Missing required parameters raise ValueErrors
   - All tool errors are logged with full context

### Code Quality
- Use descriptive names for variables, functions, and classes
- Favor clarity and readability over brevity
- Keep functions focused - max 50 lines per function
- Use type hints consistently
- Scripts with hashed suffixes (ending _xxxxxxxx) must be refactored to:
  - Follow project naming conventions
  - Implement proper error handling
  - Use centralized configuration
  - Include type hints and docstrings
  - Meet test coverage requirements
- Include Google-style docstrings for all public functions/classes
- Handle errors gracefully using try-except blocks
- Add comments to explain complex business logic
- Break complex operations into smaller, well-defined functions
- Follow PEP 8 style guidelines

### Project Structure
- Keep related functionality in module-specific directories
- Use __init__.py files to define public API for modules
- Follow the prescribed directory structure from CONVENTIONS.md
- Keep test files parallel to implementation code

# Project Folder Structure

The `dewey` project follows this general folder structure:

dewey/
├── src/
│   └── dewey/
│       ├── init.py
│       ├── core/
│       │   ├── init.py
│       │   ├── crm/
│       │   │   └── ...
│       │   ├── research/
│       │   │   └── investment_performance/
│       │   │       └── ...
│       │   ├── personal/
│       │   │   └── ...
│       │   ├── accounting/
│       │   │   ├── init.py
│       │   │   ├── integration.py
│       │   │   ├── reporting.py
│       │   │   └── ...
│       │   ├── automation/
│       │   │   ├── init.py
│       │   │   ├── feedback.py
│       │   │   ├── triggers.py
│       │   │   └── ...
│       ├── llm/
│       │   ├── init.py
│       │   ├── api_clients/
│       │   │   └── deepinfra.py
│       │   ├── prompts/
│       │   │   └── ...
│       │   ├── llm_utils.py
│       │   └── ...
│       ├── pipeline/
│       │   ├── init.py
│       │   ├── read.py
│       │   ├── resolve.py
│       │   ├── unify.py
│       │   ├── enrich.py
│       │   └── analyze.py
│       └── utils/
│           ├── init.py
│           └── ...
├── ui/
│   ├── init.py
│   ├── screens/
│   │   ├── init.py
│   │   ├── crm_screen.py
│   │   ├── research_screen.py
│   │   ├── personal_screen.py
│       │   ├── accounting_screen.py
│       │   └── ...
│   ├── components/
│   │   ├── init.py
│   │   └── navigation_bar.py
│   └── ...
├── config/
│   ├── init.py
│   ├── api_keys.yaml
│   ├── database.yaml
│   └── ...
├── tests/
│   ├── core/
│   │   ├── test_crm.py
│       │   ├── test_research.py
│       │   ├── test_accounting.py
│       │   └── test_automation.py
│   ├── llm/
│   │   └── test_llm_utils.py
│   ├── pipeline/
│   │   ├── test_read.py
│   │   ├── test_enrich.py
│       │   └── ...
│   ├── ui/
│   │   ├── test_screens.py
│   │   └── test_components.py
│   └── test_utils.py
├── docs/
├── deploy/
├── .env
├── .gitignore
├── README.md
├── pyproject.toml
└── LICENSE


**Environment Setup**

1.  **Python Version:** Ensure you are using Python 3.12 or later.
2.  **Install uv:** If you haven't already, install `uv`:
    ```bash
    pip install uv
    ```
3.  **Create Virtual Environment:** Create a virtual environment using `uv`:
    ```bash
    uv venv
    ```
4.  **Activate Virtual Environment:** Activate the virtual environment (see "Package Management" section for details).
5.  **Install Dependencies:** Install the project dependencies from `pyproject.toml`:
    ```bash
    uv pip install -r pyproject.toml
    ```

**Task Management**

Maintain a list of tasks, bugs, and features in a `TODO.md` file at the project root.

**Decision Logging**

Consider keeping a log of significant architectural and design decisions in a `decisions.md` file in the `docs/` directory.

**Code Review (Self-Review)**

Before finalizing a feature or bug fix, take some time to review your own code. Look for potential errors, areas for improvement in clarity or efficiency, and ensure it adheres to these coding conventions.

**Branching Strategy**

Use the `main` branch for the stable, production-ready code. For new features or significant changes, create a new branch from `main` (e.g., `feature/new-crm-functionality`). Once the work is complete and reviewed (self-reviewed), merge it back into `main`.

**Documentation Practices**

* **In-code Documentation:** Ensure all functions and classes have clear and comprehensive docstrings.
* **README Files:** Include `README.md` files at the root level and within sub-directories (e.g., `src/dewey/core/crm/README.md`) to provide context and usage instructions for specific modules or components.
* **Diagrams:** Keep the `docs/process.mmd` diagram updated to reflect the overall architecture and data flow.

**Testing Philosophy**

* **Test Early and Often:** Write tests as you develop new features or fix bugs.
* **Focus on Integration Tests:** Given the modular nature of `dewey`, prioritize integration tests to ensure different parts of the system work together correctly.
* **Aim for Reasonable Coverage:** While 100% coverage might not always be feasible, strive for high coverage in critical areas of the codebase.
* **Keep Tests Independent:** Ensure tests can be run in any order without affecting each other.
* **Write Clear and Readable Tests:** Tests should be easy to understand and should clearly indicate what is being tested and what the expected outcome is.

**Style Guide Enforcement**

Use Ruff to automatically format your code and identify potential style issues. Regularly run:

```bash
uv run ruff check .
uv run ruff format .
```

**Pre-commit Automation**  
Set up pre-commit hooks to enforce quality gates:
```bash
pip install pre-commit
pre-commit install
```

Package Management

Using uv:
- Create/update venv: `uv venv`
- Install deps: `uv pip install -r pyproject.toml` 
- Update lockfile: `uv pip compile pyproject.toml`
- Upgrade packages: `uv pip install --upgrade -r pyproject.toml`

Secrets Management

- Store credentials in .env file at project root
- Add .env to .gitignore 
- Use python-dotenv to load environment variables
- Never commit secrets to version control
- Use different secrets for development vs production
- Rotate API keys quarterly or when compromised

[file:*.py]

File-level settings for Python files
Maximum line length (characters)
max-line-length = 100

Indentation (spaces)
indent-size = 4

Docstrings
Use Google-style docstrings (https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
Include Args, Returns, and Raises sections as needed.
Start docstrings with a concise summary of the function/class.
docstring-style = google

Type Hints
Use type hints for function arguments and return values.
Use the typing module for complex types (e.g., List, Dict, Tuple).
Use Optional for arguments that can be None.
type-hints = required

Error Handling
error-handling = try-except

Logging
Use the logging module for logging messages.
Use different log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL) appropriately.
Include informative log messages, especially for errors and unexpected conditions.
logging = required
logging-level = INFO

Specific Function/Code Patterns
Use Ibis for all database interactions.
Avoid raw SQL queries whenever possible.
When using the DeepInfra API, handle potential errors (network errors, rate limits, etc.).
When constructing prompts for DeepInfra, be as explicit and detailed as possible.
When parsing JSON responses from DeepInfra, validate the structure and content.
Prefer Ibis's built in functions
use-ibis-functions = true
avoid-raw-sql = true

Package Management (uv)
Use uv for package management.
- Create a virtual environment: uv venv
- Install dependencies: uv pip install -r pyproject.toml
- Freeze dependencies: uv pip freeze > pyproject.toml
- Run scripts/tests within the venv: uv run python your_script.py or uv run pytest
package-manager = uv
requirements-file = pyproject.toml

Version Control (Git)
Use Git for version control.
Create a .gitignore file to exclude unnecessary files (e.g., virtual environment, caches).
Write clear and concise commit messages.
Use feature branches for new development.
Example .gitignore:
.venv/
pycache/
*.pyc
.DS_Store
.env # exclude local .env files
version-control = git
gitignore = [".venv/", "pycache/", "*.pyc", ".DS_Store", ".env"]

Code Formatting (Ruff)
Use Ruff for code formatting and linting.
- Install Ruff: uv pip install ruff
- Run Ruff: uv run ruff check . (checks)
- Run Ruff: uv run ruff format . (formats)
Consider adding Ruff to your pre-commit hooks.
code-formatter = ruff
linter = ruff

Pre-commit Hooks (Optional, but Highly Recommended)
Use pre-commit hooks to automatically run checks (formatting, linting, etc.) before committing.
- Install pre-commit: pip install pre-commit
- Create a .pre-commit-config.yaml file.
- Run pre-commit install to set up the hooks.
pre-commit = true
pre-commit-config = .pre-commit-config.yaml

Recommendations for pre-commit hooks (to be added to .pre-commit-config.yaml):
- Code Formatting (Ruff): Automatically format code to adhere to style guidelines.
- Linting (Ruff): Catch potential errors and style violations.
- Trailing Whitespace: Remove unnecessary whitespace at the end of lines.
- End-of-File Fixer: Ensure files end with a newline.
- Check for Added Large Files: Prevent accidentally committing large files.
- Check JSON: Validate JSON files.
- Check YAML: Validate YAML files.
- Detect Private Key: Prevent committing private keys.
- Check Merge Conflicts: Ensure merge conflicts are resolved before committing.
- Pyupgrade: Automatically upgrade syntax for newer Python versions.
- No commit to branch: Prevent committing to main/master.
pre-commit-recommendations = [
"ruff (formatting)",
"ruff (linting)",
"trailing-whitespace",
"end-of-file-fixer",
"check-added-large-files",
"check-json",
"check-yaml",
"detect-private-key",
"check-merge-conflict",
"pyupgrade",
"no-commit-to-branch"
]

Example .pre-commit-config.yaml:
```yaml
repos:
- repo: https://github.com/astral-sh/ruff-pre-commit
  rev: v0.1.6
  hooks:
    - id: ruff
      args: [--fix, --exit-non-zero-on-fix]
- repo: https://github.com/pre-commit/pre-commit-hooks
  rev: v4.5.0
  hooks:
    - id: trailing-whitespace
    - id: end-of-file-fixer
    - id: check-yaml
    - id: check-added-large-files
    - id: detect-private-key
```
3-2-1 Backup Strategy
Maintain at least three (3) copies of your data:
- 2 local copies on different storage media.
- 1 offsite copy.
Specific locations for this project:
1. Process-Specific DuckDB File: The individual DuckDB file created during a specific data processing run (e.g., data/processed_2024-03-14.duckdb). This is transient.
2. Joined Master DuckDB File: The central, merged DuckDB database (e.g., merged.duckdb). This is a local, persistent copy.
3. MotherDuck Cloud Instance: A backup in the MotherDuck cloud service. This is the offsite copy.
Backup Procedure (to be automated):
1. After each successful data processing run:
a. Copy the joined master DuckDB file (merged.duckdb) to a separate location (e.g., a backup drive, network share). Timestamp the backup file.
b. Use the MotherDuck CLI or Python API to upload the joined master DuckDB file to your MotherDuck account.
backup-strategy = 3-2-1
backup-locations = [
"Process-Specific DuckDB File (Transient)",
"Joined Master DuckDB File (Local, Persistent)",
"MotherDuck Cloud Instance (Offsite)",
]
backup-procedure = """

After each successful data processing run: a. Copy the joined master DuckDB file (merged.duckdb) to a separate local location. Timestamp the backup file. b. Upload the joined master DuckDB file to your MotherDuck account. """
[file:tests/*.py]

Settings for test files (assuming you're using pytest)
Test files should be in a separate tests directory.
Test function names should start with test_.
Use assertions to verify the expected behavior of your code.
Write tests for different scenarios, including edge cases and error conditions.
test-prefix = test_
test-framework = pytest

Ibis-Specific Testing Guidance:
- Use the Ibis testing framework for backend-agnostic tests: https://ibis-project.org/reference/backendtest
- Utilize Ibis test fixtures (e.g., con, alltypes, lineitem) where appropriate.
- Test against multiple backends (at least DuckDB) if feasible. Use pytest.mark.parametrize.
- Focus on testing Ibis expressions and their transformations.
- For complex transformations, consider using the Ibis compiler to generate SQL and compare it to expected SQL.
- Test with different data inputs, including edge cases (empty tables, null values, etc.).
ibis-testing-guidelines = [
"Use Ibis testing framework: https://ibis-project.org/reference/backendtest",
"Utilize Ibis test fixtures (con, alltypes, lineitem)",
"Test against multiple backends (at least DuckDB)",
"Focus on testing Ibis expressions",
"Consider using Ibis compiler for SQL comparison",
"Test with various data inputs (edge cases)",
]

DuckDB-Specific Testing Guidance:
- Use DuckDB's SQL Logic Test (sqllogictest) framework for testing SQL queries: https://duckdb.org/docs/stable/dev/sqllogictest/writing_tests.html
- Create .test files containing SQL statements and expected results.
- Use the duckdb-test CLI to run the tests.
- Test specific DuckDB features and functions you're using.
- Test error handling (e.g., invalid SQL, data type mismatches).
- Consider using parameterized tests (test files) to cover multiple scenarios with the same query.
duckdb-testing-guidelines = [
"Use DuckDB SQL Logic Test (sqllogictest): https://duckdb.org/docs/stable/dev/sqllogictest/writing_tests.html",
"Create .test files with SQL statements and expected results",
"Use duckdb-test CLI to run tests",
"Test specific DuckDB features and functions",
"Test error handling",
"Consider parameterized tests",
]

Testing Strategy:
- Aim for high test coverage, but prioritize testing critical functionality.
- Write unit tests for individual functions and classes.
- Write integration tests to verify the interaction between different parts of the system (e.g., Ibis and DuckDB).
- Use test fixtures to set up and tear down test data.
- Use mocking/patching sparingly, and prefer integration tests when possible.
testing-strategy = [
"High test coverage (prioritize critical functionality)",
"Write unit tests",
"Write integration tests",
"Use test fixtures",
"Use mocking/patching sparingly",
]

Data Locations
Specifies the locations for input data, intermediate data, and output data.
Input Data:
- Raw input data files (DuckDB, CSV, JSON) should be stored outside the project directory.
- Organize input data by process, with each process having its own subdirectory.
- Example:
/Users/srvo/ingest_data/ # Base directory for ALL input data
├── process_1/
│ ├── process_1.duckdb
│ ├── data_1.csv
│ └── data_1.json
├── process_2/
│ ├── process_2.duckdb
│ ├── data_2.csv
│ └── data_2.json
└── ...
input-data-base-path = "/Users/srvo/ingest_data"
input-data-structure = "process-based"  # Indicates subfolders per process

Intermediate Data:
- Intermediate DuckDB files (output of process-specific transformations)
should be stored within the corresponding process subdirectory inside the input data directory.
- Example: /Users/srvo/ingest_data/process_1/intermediate.duckdb
intermediate-data-location = "Within process input data directory"

Output Data:
- The final, merged DuckDB database (or Iceberg table) should be stored within the
project directory. The default name is merged.duckdb.
- Example: ~/dewey/merged.duckdb
output-data-location = "Project root directory"
output-data-default-name = "merged.duckdb"

Pipeline Stages for dewey
pipeline-stages =
{
"name": "Read",
"responsibility": "Read data from source files using Ibis.",
"modules": ["src/dewey/utils.py", "src/dewey/schemas.py"],
"functions": ["find_files", "get_file_schema_ibis", "collect_schemas"],
"input": "Raw data files in input_data/ directory.",
"output": "Ibis table expressions and schemas.",
},
{
"name": "Resolve",
"responsibility": "Merge schemas using DeepInfra API.",
"modules": ["src/dewey/schemas.py", "src/dewey/llm/api_clients/deepinfra.py", "src/dewey/llm/prompts/..."], # Added LLM related modules
"functions": ["call_deepinfra_for_schema_resolution", "merge_schemas"],
"input": "Schemas extracted in the Read stage.",
"output": "Unified schema (dictionary).",
},
{
"name": "Unify",
"responsibility": "Create target table and insert data.",
"modules": ["src/dewey/merge.py"],
"functions": ["create_merged_table_ibis", "insert_data_into_table_ibis"],
"input": "Unified schema and Ibis table expressions.",
"output": "Populated DuckDB/Iceberg table.",
},
{
"name": "Enrich",
"responsibility": "Bring in additional data, analysis, scripts, and tools to add extra dimensionality to dataset",
"modules": ["src/dewey/llm/llm_utils.py", "src/dewey/core/research/..."], # Added LLM and potential research module
"functions": ["get_search_results", "analyze_financial_data"], # Example functions
"input": "Populated DuckDB database.",
"output": "Enriched Duckdb database.",
},
{
"name": "Analyze",
"responsibility": "Perform analysis on merged data (separate scripts/tools).",
"modules": ["src/dewey/core/accounting/reporting.py", "src/dewey/core/research/investment_performance/..."], # Example modules
"functions": ["generate_balance_sheet", "analyze_portfolio"], # Example functions
"input": "Enriched DuckDB database.",
"output": "Analysis results.",
},
]

## Database Integration Strategy

### Database Architecture
- **Primary Database:** MotherDuck cloud instance (default for all operations)
- **Local Fallback:** `/Users/srvo/dewey/dewey.duckdb`
- **Sync Schedule:** Every 6 hours via cron job

### Database Organization
1. Core Tables:
   - `emails` - Email data from Gmail integration
   - `email_analyses` - Analysis results and metadata
   - `import_checkpoints` - Import progress tracking
   - `company_context` - Company research and context data
   - `documents` - Document storage and metadata
   - `tasks` - Task tracking and automation

2. Integration Tables:
   - `sync_status` - Track synchronization state between local and cloud
   - `sync_conflicts` - Record and resolve sync conflicts
   - `schema_versions` - Track schema versions and migrations

### Synchronization Rules
1. **Default Operations:**
   - Read operations default to MotherDuck
   - Write operations replicate to both MotherDuck and local
   - Fallback to local DB if MotherDuck is unavailable

2. **Conflict Resolution:**
   - Use timestamp-based resolution (latest wins)
   - Log conflicts in `sync_conflicts` table
   - Manual review required for schema conflicts

3. **Schema Management:**
   - Schema changes must be versioned
   - Migrations must be backward compatible
   - Both databases must maintain identical schemas

### Connection Management
1. **MotherDuck:**
   - Use connection pooling
   - Implement exponential backoff for retries
   - Monitor connection health

2. **Local Database:**
   - Single connection for writes
   - Connection pool for reads
   - Regular vacuum and optimization

### Backup Strategy
1. **MotherDuck:**
   - Relies on MotherDuck's built-in replication
   - Daily snapshots retained for 30 days

2. **Local Database:**
   - Daily incremental backups
   - Weekly full backups
   - 30-day retention policy

### Performance Optimization
1. **Indexes:**
   - Create consistent indexes across both databases
   - Monitor and maintain index health
   - Regular index usage analysis

2. **Partitioning:**
   - Partition large tables by date
   - Implement consistent partitioning strategy
   - Regular partition maintenance

3. **Query Optimization:**
   - Use prepared statements
   - Implement query caching where appropriate
   - Regular query performance monitoring

### MotherDuck/Local Sync Implementation
1. **Required Pattern:**
   - **ALWAYS** use the DatabaseConnection class from `dewey.core.db.connection`
   - Database operations that modify data must use `execute` method to ensure changes are tracked
   - Never create direct connections to DuckDB or MotherDuck outside of the connection module

2. **Sync Operations:**
   - Full sync runs daily at 3 AM via scheduled job (`scripts/schedule_db_sync.py`)
   - Incremental syncs are automatically triggered after write operations
   - Manual sync can be initiated via `scripts/direct_db_sync.py --mode incremental`
   - Emergency full sync can be run via `scripts/direct_db_sync.py --mode full`

3. **Code Pattern:**
   ```python
   from dewey.core.db.connection import DatabaseConnection, get_motherduck_connection, get_connection
   
   # For most operations, use DatabaseConnection
   conn = DatabaseConnection(config)
   
   # Write operations - tracked automatically for sync
   conn.execute("INSERT INTO table_name VALUES (...)")
   
   # Read operations
   result_df = conn.execute("SELECT * FROM table_name")
   
   # Only use direct connections for special cases
   md_conn = get_motherduck_connection()  # For MotherDuck-specific operations
   local_conn = get_connection()  # For local-only operations
   ```

4. **Configuration:**
   - MotherDuck token must be in environment as `MOTHERDUCK_TOKEN`
   - Connection details are defined in `dewey.yaml` under the `db` section
   - Sync configuration is in `dewey.yaml` under `db.sync` section

5. **Monitoring:**
   - Check sync status in `dewey_sync_metadata` table
   - Monitor logs in `logs/db_sync_*.log`
   - Use `--verbose` flag for detailed sync information

[file:tests/*.py]

Settings for test files (assuming you're using pytest)
Test files should be in a separate tests directory.
Test function names should start with test_.
Use assertions to verify the expected behavior of your code.
Write tests for different scenarios, including edge cases and error conditions.
test-prefix = test_
test-framework = pytest

### Test Structure and Organization
1. **Directory Structure:**
   - Unit tests in `tests/unit/[module_path]/test_[filename].py`
   - Integration tests in `tests/integration/`
   - Test directory structure should mirror the src directory structure

2. **File Naming:**
   - Test files must be named `test_*.py`
   - Test functions must be named `test_*`
   - Test classes must be named `Test*`

3. **Required Test Components:**
   - `conftest.py` with common fixtures in each test directory
   - Proper imports with absolute paths
   - Type annotations on all test functions and fixtures
   - Docstrings for all test functions describing what is being tested

### Database Testing
1. **NEVER Connect to Real Databases:**
   - Always mock database connections in tests
   - Use `unittest.mock` to patch connection functions
   - Create mock fixtures that return pandas DataFrames

2. **Standard Database Fixtures:**
   ```python
   @pytest.fixture
   def mock_db_connection():
       """Create a mock database connection."""
       mock_conn = MagicMock()
       mock_conn.execute.return_value = pd.DataFrame({"col1": [1, 2, 3]})
       return mock_conn
   
   @pytest.fixture
   def mock_motherduck_connection():
       """Create a mock MotherDuck connection."""
       return mock_db_connection()
   ```

3. **Mocking Connection Functions:**
   ```python
   @patch("dewey.core.db.connection.get_motherduck_connection")
   @patch("dewey.core.db.connection.get_connection")
   def test_database_function(mock_get_conn, mock_get_motherduck, mock_db_connection):
       # Arrange
       mock_get_conn.return_value = mock_db_connection
       mock_get_motherduck.return_value = mock_db_connection
       
       # Act
       result = function_under_test()
       
       # Assert
       assert result is not None
       mock_db_connection.execute.assert_called_once()
   ```

### Testing External Dependencies
1. **Mock ALL External Dependencies:**
   - API calls (patch requests, httpx, etc.)
   - File system operations (patch open, Path.exists, etc.)
   - Environment variables
   - LLM calls and responses
   - Time-dependent functions

2. **Standard Pattern for File Operations:**
   ```python
   @patch("pathlib.Path.exists")
   @patch("builtins.open", new_callable=mock_open, read_data="test data")
   def test_file_operations(mock_file_open, mock_exists):
       # Arrange
       mock_exists.return_value = True
       
       # Act
       result = function_under_test("file.txt")
       
       # Assert
       mock_file_open.assert_called_once_with("file.txt", "r")
       assert result == "test data"
   ```

### Test Fixtures and Setup
1. **Use Fixtures for All Setup:**
   - Common test data should be defined in fixtures
   - Complex object creation should be in fixtures
   - Environment setup/teardown should be handled by fixtures
   - Use fixture scope appropriately (function, class, module, session)

2. **Fixture Patterns:**
   - Use `@pytest.fixture` decorator
   - Add type annotations to fixtures
   - Document fixtures with docstrings
   - Return test objects from fixtures
   - Use `yield` for fixtures that need teardown

3. **BaseScript Testing:**
   ```python
   @pytest.fixture
   def mock_base_script() -> MagicMock:
       """Mock BaseScript instance."""
       mock_script = MagicMock(spec=BaseScript)
       mock_script.get_config_value.return_value = "test_value"
       mock_script.logger = MagicMock()
       return mock_script
   
   @patch("dewey.core.base_script.BaseScript.__init__", return_value=None)
   def test_script_class(mock_init, mock_base_script):
       # Test code that uses BaseScript
       pass
   ```

### Assertion Best Practices
1. **Complete Assertions:**
   - Assert both function results and side effects
   - Verify all expected method calls
   - Check for expected exceptions with `pytest.raises`
   - Verify log messages when relevant

2. **Parameterized Tests:**
   ```python
   @pytest.mark.parametrize(
       "input_value,expected_result",
       [
           (1, 2),
           (2, 4),
           (3, 6),
           (-1, -2),
           (0, 0),
       ],
   )
   def test_double_function(input_value: int, expected_result: int) -> None:
       """Test that double() correctly multiplies values by 2."""
       assert double(input_value) == expected_result
   ```

3. **Testing Exceptions:**
   ```python
   def test_value_error_raised():
       """Test that ValueError is raised for invalid inputs."""
       with pytest.raises(ValueError) as exc_info:
           function_under_test(-1)
       assert "Invalid input" in str(exc_info.value)
   ```

Ibis-Specific Testing Guidance:
- Use the Ibis testing framework for backend-agnostic tests: https://ibis-project.org/reference/backendtest
- Utilize Ibis test fixtures (e.g., con, alltypes, lineitem) where appropriate.
- Test against multiple backends (at least DuckDB) if feasible. Use pytest.mark.parametrize.
- Focus on testing Ibis expressions and their transformations.
- For complex transformations, consider using the Ibis compiler to generate SQL and compare it to expected SQL.
- Test with different data inputs, including edge cases (empty tables, null values, etc.).
ibis-testing-guidelines = [
"Use Ibis testing framework: https://ibis-project.org/reference/backendtest",
"Utilize Ibis test fixtures (con, alltypes, lineitem)",
"Test against multiple backends (at least DuckDB)",
"Focus on testing Ibis expressions",
"Consider using Ibis compiler for SQL comparison",
"Test with various data inputs (edge cases)",
]

DuckDB-Specific Testing Guidance:
- Use DuckDB's SQL Logic Test (sqllogictest) framework for testing SQL queries: https://duckdb.org/docs/stable/dev/sqllogictest/writing_tests.html
- Create .test files containing SQL statements and expected results.
- Use the duckdb-test CLI to run the tests.
- Test specific DuckDB features and functions you're using.
- Test error handling (e.g., invalid SQL, data type mismatches).
- Consider using parameterized tests (test files) to cover multiple scenarios with the same query.
duckdb-testing-guidelines = [
"Use DuckDB SQL Logic Test (sqllogictest): https://duckdb.org/docs/stable/dev/sqllogictest/writing_tests.html",
"Create .test files with SQL statements and expected results",
"Use duckdb-test CLI to run tests",
"Test specific DuckDB features and functions",
"Test error handling",
"Consider parameterized tests",
]

Testing Strategy:
- Aim for high test coverage, but prioritize testing critical functionality.
- Write unit tests for individual functions and classes.
- Write integration tests to verify the interaction between different parts of the system (e.g., Ibis and DuckDB).
- Use test fixtures to set up and tear down test data.
- Use mocking/patching sparingly, and prefer integration tests when possible.
testing-strategy = [
"High test coverage (prioritize critical functionality)",
"Write unit tests",
"Write integration tests",
"Use test fixtures",
"Use mocking/patching sparingly",
]


