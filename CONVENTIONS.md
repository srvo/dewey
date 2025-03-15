# .aider.conf - Coding Conventions for dewey Project

# Maintenance Principle
- Keep TODO.md updated as the single source of truth for tasks
- Update priorities weekly or when major milestones are reached
- Preserve completed tasks in "Completed/Migrated" section for reference

# General Guidelines
- Use descriptive names for variables, functions, and classes
- Favor clarity and readability over brevity
- Keep functions relatively short and focused on a single task
- Use type hints consistently
- Include docstrings for all functions and classes
# .aider.conf - Coding Conventions for dewey Project

# General Guidelines

# Use descriptive names for variables, functions, and classes.
# Favor clarity and readability over brevity.
# Keep functions relatively short and focused on a single task.
# Use type hints consistently.
# Include docstrings for all functions and classes.
# Handle errors gracefully using try-except blocks.
# Add comments to explain complex logic.
# Break down complex operations into smaller, well-defined functions.
# Follow PEP 8 (https://peps.python.org/pep-0008/) style guidelines.

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

1.  **Python Version:** Ensure you are using a compatible Python version (e.g., Python 3.11 or later).
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

Use Ruff to automatically format your code and identify potential style issues. Regularly run the following commands:

```bash
uv run ruff check .
uv run ruff format .
Consider setting up pre-commit hooks to automate these checks before each commit.

Dependency Management

Use uv to manage project dependencies. Keep your dependencies up-to-date by periodically checking for new versions and updating them in your pyproject.toml file.

Secrets Management

Store sensitive information like API keys in a .env file at the root of the project. Ensure that .env is added to your .gitignore file to prevent accidentally committing it to the repository. Use a library like python-dotenv to load these environment variables into your application.

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

Example .pre-commit-config.yaml (PLACEHOLDER - Needs to be filled in later):
repos:
# Add hook configurations here, based on the recommendations above.
# See https://pre-commit.com/hooks.html for available hooks.
pass
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


