# Dewey Project: Unified Development Guidelines & Conventions (PostgreSQL Edition)
# 1. Core Philosophy & Principles
Simplicity & Maintainability: Prioritize simple, clear solutions. Avoid unnecessary complexity. Write code that is easy to understand and maintain.
Iterate, Don't Reinvent: Prefer iterating on existing, working code rather than building entirely new solutions unless fundamentally necessary or explicitly requested.
Focus: Concentrate efforts on the specific task assigned. Avoid unrelated changes or scope creep.
Quality: Strive for a clean, organized, well-tested, secure, and robust codebase adhering to these guidelines.
Adherence to Conventions: These guidelines are mandatory for all development work on the Dewey project.
Collaboration: This document guides both human developers and AI assistants for effective teamwork. Use clear communication and leverage strengths appropriately.
# 2. Project Setup & Environment
Python Version: Use Python 3.12 or later.
Package Management (uv):
Install uv: pip install uv
Create Virtual Environment: uv venv
Activate Virtual Environment: (Follow platform-specific activation command shown by uv venv)
Install Dependencies: uv pip install -r pyproject.toml (Ensure PostgreSQL driver like psycopg2-binary or asyncpg is included).
Update Lockfile: uv pip compile pyproject.toml --output-file pyproject.toml
Upgrade Packages: uv pip install --upgrade -r pyproject.toml
Run commands in venv: uv run <command> (e.g., uv run python your_script.py, uv run pytest)
Dependencies:
Manage all Python dependencies via pyproject.toml. Include necessary PostgreSQL drivers and potentially an ORM like SQLAlchemy.
Minimize external dependencies, especially for core components. Document the rationale for adding new dependencies.
Secrets Management:
Store all secrets (API keys, DB passwords) in a .env file at the project root.
Never commit the .env file to version control. Ensure .env is listed in .gitignore.
Use python-dotenv (or similar mechanism provided by frameworks/BaseScript) to load environment variables.
Use distinct secrets for development and production environments.
Rotate secrets regularly (e.g., quarterly) or immediately if compromised.
# 3. Version Control (Git)
Branching Strategy:
main branch contains stable, production-ready code.
Create feature branches from main for new development (e.g., feature/new-crm-functionality).
Merge completed and reviewed feature branches back into main. Squash commits before merging for a clean history.
Commit Hygiene:
Commit frequently with clear, concise, atomic messages describing the change.
Keep the working directory clean. Ensure no unrelated, temporary, or generated files (like .pyc, .DS_Store, .venv) are staged or committed.
Use .gitignore effectively. Key entries include: .venv/, __pycache__/, *.pyc, .DS_Store, .env, *script_checkpoints.yaml, potentially data directories if large/transient.
Pre-commit Hooks:
Highly recommended to enforce quality gates automatically before committing.
Install: pip install pre-commit
Setup: pre-commit install
Configure hooks in .pre-commit-config.yaml. Recommended hooks:
ruff (formatting & linting)
trailing-whitespace
end-of-file-fixer
check-yaml, check-json
check-added-large-files
detect-private-key
check-merge-conflict
pyupgrade
no-commit-to-branch (configure for main/master)
# 4. Project Structure & Organization
Adhere strictly to the defined project structure: (Structure remains largely the same, specific file contents within core/db will change)

dewey/
├── src/
│   └── dewey/               # Main application source code
│       ├── __init__.py
│       ├── core/            # Core business logic modules
│       │   ├── __init__.py
│       │   ├── base_script.py # MANDATORY Base class for scripts
│       │   ├── db/
│       │   │   └── connection.py # Central PostgreSQL connection logic & pooling
│       │   ├── engines/       # Integration engines (Search, etc.)
│       │   │   └── base.py
│       │   ├── crm/
│       │   ├── research/
│       │   ├── personal/
│       │   ├── accounting/
│       │   └── automation/
│       ├── llm/             # Language Model interactions
│       │   ├── __init__.py
│       │   ├── agents/
│       │   ├── api_clients/
│       │   └── prompts/
│       ├── pipeline/        # Data processing pipeline stages
│       │   ├── __init__.py
│       │   # ... pipeline stages ...
│       └── utils/           # Shared utility functions
│           └── __init__.py
├── ui/                      # User Interface components (if applicable)
│   # ... ui structure ...
├── config/                  # Centralized configuration ONLY
│   ├── __init__.py
│   └── dewey.yaml           # Primary configuration file (including DB connection details)
├── tests/                   # All test code
│   ├── conftest.py          # Root test configurations/fixtures
│   ├── unit/                # Unit tests (mirroring src structure)
│   │   └── core/
│   │       └── test_base_script.py
│   └── integration/         # Integration tests
│       └── test_db_interactions.py # Example
├── docs/                    # Documentation
│   # ... docs structure ...
├── scripts/                 # Utility/operational scripts (e.g., migrations)
│   └── run_migrations.py   # Example
├── .env                     # Local environment variables (DO NOT COMMIT)
├── .env.example             # Example environment file
├── .gitignore
├── README.md                # Project overview, setup, core concepts
├── pyproject.toml           # Dependencies and project metadata
├── TODO.md                  # Central task tracking
└── .pre-commit-config.yaml  # Pre-commit hook configuration
# 5. Configuration Management
Centralized Configuration: All system configuration MUST reside in config/dewey.yaml.
No module-specific YAML files are allowed (exception: transient script_checkpoints.yaml if necessary, containing only file hashes).
Structure: core, vector_stores, llm, pipeline, prd, formatting, db, engines, etc.
The db section should contain PostgreSQL connection parameters: host, port, user, database, schema (optional), etc. Sensitive values like password MUST be referenced from environment variables using ${VAR_NAME} syntax (e.g., password: ${DB_PASSWORD}).
Paths within config files are relative to the project root.
Environment Variables: Use ${VAR_NAME} syntax within dewey.yaml to reference secrets or environment-specific settings stored in .env.
Validation: Config sections should ideally validate themselves upon loading (e.g., using Pydantic).
Access: Scripts (especially those inheriting BaseScript) should access configuration through a standardized mechanism, typically provided by the base class.
# 6. Coding Standards & Best Practices
## A. General (Same as before)
Readability: Write clean, well-organized code. Favor clarity over excessive brevity.
DRY (Don't Repeat Yourself): Actively look for and reuse existing functionality. Refactor to eliminate duplication.
Keep it Small: Aim for Python functions under 50 lines, focused files (~300 lines), and small single-responsibility classes/components.
Error Handling: Use explicit exceptions, log contextually, use try...except...finally and with, fix root causes.
Logging: Use standard logging via BaseScript, appropriate levels, contextual messages.
Language: All code, docs, comments, commits must be in English.
## B. Python Specifics ([file:*.py])
Formatting: Use Black (line length 88) and Ruff (linting). Enforce via pre-commit.
Imports: Absolute imports, grouped (standard, third-party, local), sorted alphabetically (via tools).
Naming Conventions: snake_case (variables, functions, methods), PascalCase (classes, types), UPPER_CASE (constants), _ prefix for internal elements.
Type Hints: Required for all function/method arguments and return values. Use typing module.
Docstrings: Required for all public modules, classes, functions. Use Google-style. Include Args:, Returns:, Raises:, examples.
Database Interaction:
Use the chosen data access layer consistently (e.g., SQLAlchemy ORM/Core, psycopg2, or Ibis configured for PostgreSQL).
Crucially, always use parameterized queries to prevent SQL injection vulnerabilities. Do not use f-strings or string concatenation to build SQL queries with external input.
If using an ORM, understand session management and transaction boundaries.
Hashed Suffix Scripts: Still considered temporary and must be refactored into permanent, well-structured code following all conventions.
# 7. Core Development Frameworks & Patterns
## A. BaseScript Framework (Mandatory)
Requirement: ALL non-test Python scripts MUST inherit from dewey.core.base_script.BaseScript. Enforced via CI/PR checks.
Purpose: Provides standardized setup, configuration loading, logging, PostgreSQL connection pooling and management, error handling.
Implementation: (Conceptual structure remains; internal DB handling changes)
Python

from dewey.core.base_script import BaseScript
from dewey.config import Config # Assuming a config loading mechanism
# May need specific DB types if using SQLAlchemy Sessions etc.
# from sqlalchemy.orm import Session

class MyCustomScript(BaseScript):
    def __init__(self, config: Config):
        super().__init__(
            config=config,
            config_section='my_custom_section',
            requires_db=True, # Enable DB connection pool via base
            enable_llm=False
        )
        # Additional script-specific initialization

    def run(self):
        """Main execution logic for the script."""
        self.logger.info(f"Starting MyCustomScript...")
        # Example with SQLAlchemy session (if applicable)
        # with self.db_session_scope() as session:
        #    # Perform DB operations using session
        #    result = session.query(MyModel).filter(...).all()
        #    self.logger.info(f"Found {len(result)} items.")

        # Example with direct connection/cursor (if applicable)
        # with self.db_connection() as conn:
        #     with conn.cursor() as cursor:
        #         cursor.execute("SELECT COUNT(*) FROM my_table WHERE condition = %s", (param_value,))
        #         count = cursor.fetchone()[0]
        #         self.logger.info(f"Found {count} rows matching condition.")

        self.logger.info("MyCustomScript finished successfully.")

# Example runner remains similar
Rules: Implement run(), use self.logger, access config via base, use DB connections/sessions provided by the base class (e.g., self.db_connection(), self.db_session_scope()), leverage base error handling.
Prohibited: Standalone scripts, direct logging config, direct DB connection/pool creation outside core.db.connection, manual config parsing.
Exceptions: Test scripts, simple CLI entry points instantiating BaseScript classes.
## B. Agent & Tool Configuration (LLM Integration) (No change needed related to DB)
(Content remains the same as previous version)

# 8. Database Integration (PostgreSQL)
Architecture: The application interacts with a central PostgreSQL database instance (or cluster). Details like read replicas are operational concerns but the application should connect via the configured primary host/service name.
Centralized Connection Management: MANDATORY - All database interactions must go through the abstraction layer provided in dewey.core.db.connection. This module is responsible for:
Reading connection details from the central configuration (dewey.yaml).
Establishing connections to PostgreSQL.
Managing connection pooling (essential for performance with PostgreSQL). Use libraries like SQLAlchemy's pooling or psycopg2's pool managers.
Data Access Layer: Use the project's chosen data access method consistently (e.g., SQLAlchemy ORM/Core, direct psycopg2 with helper functions, Ibis). Ensure it's compatible with PostgreSQL and uses parameterized queries.
Schema Management & Migrations:
Database schema changes must be managed using a migration tool (e.g., Alembic if using SQLAlchemy, or alternatives like dbmate, flyway).
Migrations must be version-controlled and applied consistently across environments.
Develop migrations to be backward-compatible where feasible.
Backup Strategy: A robust PostgreSQL backup strategy is an operational requirement. While not strictly code-level, developers should be aware:
Standard tools include pg_dump for logical backups and pg_basebackup / Point-in-Time Recovery (PITR) using Write-Ahead Log (WAL) archiving for continuous backups.
The 3-2-1 backup principle still applies: 3 copies, 2 local media, 1 offsite (e.g., backups stored in cloud storage like S3).
# 9. Testing & Validation
## A. Philosophy & Strategy (Same as before)
Test Early, Test Often.
Test Types: Unit (tests/unit/), Integration (tests/integration/).
Coverage: Aim for high coverage, especially for critical paths.
TDD: Recommended (Outline->Fail->Pass->Refactor). For bugs: Reproduce->Fail->Fix->Pass.
Tests Must Pass: Mandatory for commits/merges.
## B. Implementation ([file:tests/*.py])
Framework: Use pytest.
Location & Naming: Mirror src in tests/unit, tests/integration. Files test_*.py, functions test_*, classes Test*.
Mocks are Mandatory for External Systems:
NEVER connect to a live development or production PostgreSQL database in automated tests.
Use unittest.mock (@patch, MagicMock).
Mock the database interaction layer:
Patch the functions that create connections/sessions (e.g., psycopg2.connect, SQLAlchemy create_engine, sessionmaker, or methods within your DatabaseConnection class).
Return mock connection/session/cursor objects. Configure return values for methods like execute, Workspaceone, Workspaceall, or ORM query methods (all(), first(), etc.) often using pandas.DataFrame or mock model instances.
Mock other external systems: file system, APIs, LLMs, environment variables, time (datetime).
Fixtures (conftest.py, @pytest.fixture): Use extensively for setup/teardown (test data, mock objects, config). Use scopes effectively.
Assertions: Use clear asserts, verify return values AND side effects (mock calls), test exceptions (pytest.raises), check logs (caplog).
Parameterization (@pytest.mark.parametrize): Use for testing various inputs/outputs/edge cases.
Database-Specific Testing:
Focus testing on your application's interaction logic with the mocked database layer.
If using an ORM like SQLAlchemy, you can test model logic or simple queries against an in-memory SQLite database via fixtures, but be aware of SQL dialect differences between SQLite and PostgreSQL. Use this cautiously and prioritize mocking the actual PostgreSQL interface.
Remove previous DuckDB-specific testing guidance (e.g., sqllogictest).
If using Ibis, ensure tests cover PostgreSQL-specific behavior if relying on backend-specific functions.
# 10. Documentation (Same as before)
In-Code: Mandatory Google-style docstrings.
READMEs: Project root and key module READMEs.
Architecture & Design: docs/architecture.md, docs/technical.md, docs/decisions.md, docs/process.mmd.
PRDs: Store in docs/prds/, track in dewey.yaml, follow structure, update regularly.
Task Tracking: TODO.md is the single source of truth.
Updates: Crucially, keep all documentation synchronized with code changes.
# 11. AI Collaboration (Same as before)
Clarity: Clear, specific instructions.
Context: Remind AI of relevant history.
Suggest vs. Apply: Be explicit. Use 'apply' cautiously.
Critical Review: Humans MUST review ALL AI code. Verify logic, conventions, tests.
Focus: Guide AI on specific parts.
Leverage Strengths: Boilerplate, refactoring patterns, syntax, test cases. Human oversight for complexity, architecture, security.
Incremental Interaction: Break down tasks, review steps.
Standard Check-in: AI confirms understanding before proceeding.
# 12. Maintenance & Processes
TODO Management: Keep TODO.md updated (priorities, details, history).
Shell Aliases: Maintain useful, documented aliases.
Function Consolidation: Follow process for refactoring temporary/hashed scripts.
Refactoring: Purposeful (clarity, DRY, architecture). Edit in place. Verify integrations.
Debugging: Root cause focus, check logs, targeted logging (temporary), check docs/decisions.md, document complex fixes.
Backup Strategy (3-2-1): Ensure operational PostgreSQL backups follow this principle (e.g., pg_dump/PITR to local disk + offsite storage like S3).
Guidelines Update: Periodically review and update this document.
