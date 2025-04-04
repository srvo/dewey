# Dewey Project: Unified Development Guidelines & Conventions (PostgreSQL Edition)

## 1. Core Philosophy & Principles

### Simplicity & Maintainability
- Prioritize simple, clear solutions
- Avoid unnecessary complexity
- Write code that is easy to understand and maintain

### Iterate, Don't Reinvent
- Prefer iterating on existing, working code rather than building entirely new solutions unless fundamentally necessary or explicitly requested
- Prefer using popular packages and libraries over generating custom code -- unless the library does not exist or is not a good fit

### Focus
- Concentrate efforts on the specific task assigned
- Avoid unrelated changes or scope creep

### Quality
- Strive for a clean, organized, well-tested, secure, and robust codebase adhering to these guidelines
- If you feel that you don't have enough information to complete the task, ask for clarification
- Feel free to ask questions and seek clarification if you are unsure about the requirements or the best way to complete the task, even if it's not explicitly stated in the task or your question is potentially blunt/rude

### Adherence to Conventions
- These guidelines are mandatory for all development work on the Dewey project

### Collaboration
- This document guides both human developers and AI assistants for effective teamwork
- Use clear communication and leverage strengths appropriately

## 2. Project Setup & Environment

### Python Version
- Use Python 3.12 or later

### Package Management (uv)
1. Install uv: `pip install uv`
2. Create Virtual Environment: `uv venv`
3. Activate Virtual Environment: (Follow platform-specific activation command shown by uv venv)
4. Install Dependencies: `uv pip install -r pyproject.toml` (Ensure PostgreSQL driver like psycopg2-binary or asyncpg is included)
5. Update Lockfile: `uv pip compile pyproject.toml --output-file pyproject.toml`
6. Upgrade Packages: `uv pip install --upgrade -r pyproject.toml`
7. Run commands in venv: `uv run <command>` (e.g., `uv run python your_script.py`, `uv run pytest`)

### Dependencies
- Manage all Python dependencies via pyproject.toml
- Include necessary PostgreSQL drivers and potentially an ORM like SQLAlchemy
- Minimize external dependencies, especially for core components
- Document the rationale for adding new dependencies

### Secrets Management
- Store all secrets (API keys, DB passwords) in a .env file at the project root
- Never commit the .env file to version control
- Ensure .env is listed in .gitignore
- Use python-dotenv (or similar mechanism provided by frameworks/BaseScript) to load environment variables
- Use distinct secrets for development and production environments
- Rotate secrets regularly (e.g., quarterly) or immediately if compromised

## 3. Version Control (Git)

### Branching Strategy
- `main` branch contains stable, production-ready code
- Create feature branches from main for new development (e.g., `feature/new-crm-functionality`)
- Merge completed and reviewed feature branches back into main
- Squash commits before merging for a clean history

### Commit Hygiene
- Commit frequently with clear, concise, atomic messages describing the change
- Keep the working directory clean
- Ensure no unrelated, temporary, or generated files (like .pyc, .DS_Store, .venv) are staged or committed
- Use .gitignore effectively. Key entries include: .venv/, __pycache__/, *.pyc, .DS_Store, .env, *script_checkpoints.yaml, potentially data directories if large/transient.

### Pre-commit Hooks
- Highly recommended to enforce quality gates automatically before committing
- Installation: `pip install pre-commit`
- Setup: `pre-commit install`
- Configure hooks in .pre-commit-config.yaml. Recommended hooks:
  - ruff (formatting & linting)
  - trailing-whitespace
  - end-of-file-fixer
  - check-yaml, check-json
  - check-added-large-files
  - detect-private-key
  - check-merge-conflict
  - pyupgrade
  - no-commit-to-branch (configure for main/master)

## 4. Project Structure & Organization

Adhere strictly to the defined project structure: (Structure remains largely the same, specific file contents within core/db will change)

```
dewey/
├── src/
│ └── dewey/ # Main application source code
│ ├── __init__.py
│ ├── core/ # Core business logic modules
│ │ ├── __init__.py
│ │ ├── base_script.py # MANDATORY Base class for scripts
│ │ ├── db/
│ │ │ └── connection.py # Central PostgreSQL connection logic & pooling
│ │ ├── engines/ # Integration engines (Search, etc.)
│ │ │ └── base.py
│ │ ├── crm/
│ │ ├── research/
│ │ ├── personal/
│ │ ├── accounting/
│ │ └── automation/
│ ├── llm/ # Language Model interactions
│ │ ├── __init__.py
│ │ ├── agents/
│ │ ├── api_clients/
│ │ └── prompts/
│ ├── pipeline/ # Data processing pipeline stages
│ │ ├── __init__.py
│ │ # ... pipeline stages ...
│ └── utils/ # Shared utility functions
│ └── __init__.py
├── ui/ # User Interface components (if applicable)
│ # ... ui structure ...
├── config/ # Centralized configuration ONLY
│ ├── __init__.py
│ └── dewey.yaml # Primary configuration file (including DB connection details)
├── tests/ # All test code
│ ├── conftest.py # Root test configurations/fixtures
│ ├── unit/ # Unit tests (mirroring src structure)
│ │ └── core/
│ │ └── test_base_script.py
│ └── integration/ # Integration tests
│ └── test_db_interactions.py # Example
├── docs/ # Documentation
│ # ... docs structure ...
├── scripts/ # Utility/operational scripts (e.g., migrations)
│ └── run_migrations.py # Example
├── .env # Local environment variables (DO NOT COMMIT)
├── .env.example # Example environment file
├── .gitignore
├── README.md # Project overview, setup, core concepts
├── pyproject.toml # Dependencies and project metadata
├── TODO.md # Central task tracking
└── .pre-commit-config.yaml # Pre-commit hook configuration
```

## 5. Configuration Management

### Centralized Configuration
- All system configuration MUST reside in `config/dewey.yaml`
- No module-specific YAML files allowed (exception: transient `script_checkpoints.yaml` may contain only file hashes)

### Configuration Structure
Key sections should include:
- `core`
- `vector_stores`
- `llm`
- `pipeline`
- `prd`
- `formatting`
- `db`
- `engines`

### Database Configuration
The `db` section must contain PostgreSQL connection parameters:
- Required: `host`, `port`, `user`, `database`
- Optional: `schema`
- Sensitive values (like `password`) MUST use environment variable references:
  ```yaml
  password: ${DB_PASSWORD}
  ```

### Path Handling
- All paths in config files are relative to the project root

### Environment Variables
- Use `${VAR_NAME}` syntax in `dewey.yaml` to reference `.env` secrets
- Example: `${API_KEY}`

### Validation
- Config sections should self-validate on load (recommend using Pydantic)

### Access Pattern
- Scripts (especially `BaseScript` subclasses) should access config through base class mechanisms

---

## 6. Coding Standards & Best Practices

### General Principles
- **Readability**: Prioritize clean, well-organized code over brevity
- **DRY**: Actively reuse existing functionality; refactor duplicates
- **Modularity**:
  - Functions: <50 lines
  - Files: ~300 lines
  - Classes: Single responsibility
- **Error Handling**:
  - Use explicit exceptions
  - Log contextually
  - Prefer `try...except...finally` and `with` blocks
  - Fix root causes
- **Logging**:
  - Use `BaseScript` logging
  - Appropriate log levels
  - Contextual messages
- **Language**: All code/docs/comments/commits in English

### Python Specifics
- **Formatting**:
  - Black (88 char line length)
  - Ruff (linting)
  - Enforce via pre-commit
- **Imports**:
  - Absolute imports
  - Grouped (standard → third-party → local)
  - Alphabetically sorted
- **Naming**:
  - `snake_case`: variables, functions, methods
  - `PascalCase`: classes, types
  - `UPPER_CASE`: constants
  - `_prefix`: internal elements
- **Type Hints**: Required for all function/method args and returns
- **Docstrings** (Google-style):
  ```python
  """Short description.

  Longer description if needed.

  Args:
      param1: Description
      param2: Description

  Returns:
      Description of return value

  Raises:
      ValueError: When something bad happens
  """
  ```

### Database Interaction
- **Consistency**: Use chosen data access layer uniformly (SQLAlchemy, psycopg2, Ibis)
- **Security**:
  - Always use parameterized queries
  - Never use f-strings/concatenation for SQL with external input
- **ORM Usage**:
  - Understand session management
  - Be clear on transaction boundaries
- **Temporary Scripts**: Hashed suffix scripts must be refactored into permanent code

---

## 7. Core Development Frameworks & Patterns

### BaseScript Framework (Mandatory)
**Requirement**: All non-test Python scripts MUST inherit from `dewey.core.base_script.BaseScript`

**Purpose**:
- Standardized setup
- Configuration loading
- Logging
- PostgreSQL connection pooling
- Error handling

**Implementation Example**:
```python
from dewey.core.base_script import BaseScript
from dewey.config import Config

class MyCustomScript(BaseScript):
    def __init__(self, config: Config):
        super().__init__(
            config=config,
            config_section='my_custom_section',
            requires_db=True,  # Enables DB connection pool
            enable_llm=False
        )
        # Additional initialization

    def run(self):
        """Main execution logic."""
        self.logger.info("Starting script...")

        # SQLAlchemy session example:
        # with self.db_session_scope() as session:
        #     results = session.query(MyModel).all()
        #     self.logger.info(f"Found {len(results)} items")

        # Direct connection example:
        # with self.db_connection() as conn:
        #     with conn.cursor() as cursor:
        #         cursor.execute("SELECT COUNT(*) FROM table")
        #         count = cursor.fetchone()[0]

        self.logger.info("Script completed")
```

**Rules**:
- Must implement `run()`
- Use `self.logger` for logging
- Access config through base class
- Use provided DB connections (`db_connection()`, `db_session_scope()`)
- Leverage base error handling

**Prohibited**:
- Standalone scripts
- Direct logging config
- Manual DB connection/pool creation
- Manual config parsing

**Exceptions**:
- Test scripts
- Simple CLI entry points that instantiate `BaseScript`

---

## 8. Module Interactions & Decoupling

### Core Principles
- **Loose Coupling**: Modules should be loosely coupled with minimal direct dependencies
- **Interface Abstractions**: Use interfaces to define module boundaries
- **Event-Driven Architecture**: Use event system for cross-module communication
- **Dependency Injection**: Inject dependencies rather than hard-coding them

### Event System
- Use the centralized event bus for cross-module communication
- Define clear event types with documented schemas
- **Implementation**:
  ```python
  # Publishing an event
  from dewey.core.events import event_bus
  
  event_bus.publish("contact_discovered", {"name": "John Doe", "email": "john@example.com"})
  
  # Subscribing to an event
  def handle_new_contact(contact_data):
      # Process the contact data
      print(f"New contact: {contact_data['name']}")
  
  event_bus.subscribe("contact_discovered", handle_new_contact)
  ```

### Service Interfaces
- Define interfaces for module services in `dewey.core.interfaces` package
- Implementation classes should reference interfaces, not concrete types
- Example:
  ```python
  # Interface definition
  from abc import ABC, abstractmethod
  
  class LLMProvider(ABC):
      @abstractmethod
      def generate_text(self, prompt: str) -> str:
          pass
  
  # Implementation
  class OpenAIProvider(LLMProvider):
      def generate_text(self, prompt: str) -> str:
          # Implementation using OpenAI
          return "Generated text"
          
  # Usage with dependency injection
  def process_data(llm_provider: LLMProvider, data: str) -> str:
      return llm_provider.generate_text(f"Process this data: {data}")
  ```

### Dependency Injection
- Use constructor injection pattern for dependencies
- Dependencies should be optional when possible, with graceful fallbacks
- When subclassing `BaseScript`, use kwargs to pass dependencies:
  ```python
  class MyScript(BaseScript):
      def __init__(
          self, 
          llm_provider: Optional[LLMProvider] = None,
          *args, **kwargs
      ):
          super().__init__(*args, **kwargs)
          self.llm_provider = llm_provider or self._get_default_llm()
  ```

### Cross-Module Feature Development
- New features spanning multiple modules should use the event system
- Create a feature-specific coordinator that subscribes to relevant events
- Document cross-module interactions in feature documentation

---

## 9. Database Integration (PostgreSQL)

### Architecture
- Central PostgreSQL instance/cluster
- Connect via configured primary host/service name

### Connection Management
**Centralized in `dewey.core.db.connection`**:
1. Reads connection details from `dewey.yaml`
2. Establishes PostgreSQL connections
3. Manages connection pools (SQLAlchemy/psycopg2 pools)

### Data Access Layer
- Use consistently across project (SQLAlchemy, psycopg2, Ibis)
- Must support PostgreSQL
- Must use parameterized queries

### Schema Management
**Migrations**:
- Use dedicated tool (Alembic, dbmate, flyway)
- Version control all migrations
- Apply consistently across environments
- Prefer backward-compatible changes

### Backup Strategy
**Operational Requirements**:
- **Logical backups**: `pg_dump`
- **Continuous backups**: `pg_basebackup` + WAL archiving (PITR)
- **3-2-1 Principle**:
  - 3 copies
  - 2 local media types
  - 1 offsite (e.g., S3)

---

## 10. Testing & Validation

### Philosophy
- Test early and often
- High coverage (especially critical paths)
- TDD recommended (Outline → Fail → Pass → Refactor)
- Bug workflow: Reproduce → Fail → Fix → Pass
- All tests must pass before merging

### Implementation
**Framework**: pytest

**Structure**:
- `tests/unit/`: Unit tests (mirror `src` structure)
- `tests/integration/`: Integration tests
- Naming:
  - Files: `test_*.py`
  - Functions: `test_*`
  - Classes: `Test*`

**Mocking Requirements**:
- **Never** connect to live DBs in tests
- Mock all external systems:
  - Database layer (`psycopg2.connect`, SQLAlchemy sessions)
  - APIs
  - File system
  - Environment variables
  - Time (`datetime`)

**Fixtures**:
- Use extensively (`conftest.py`, `@pytest.fixture`)
- Proper scoping
- Test data setup/teardown

**Assertions**:
- Clear verification of:
  - Return values
  - Side effects
  - Exceptions (`pytest.raises`)
  - Logs (`caplog`)

**Parameterization**:
- Use `@pytest.mark.parametrize` for input/output variations

**Database Testing**:
- Focus on interaction logic with mocked DB layer
- SQLite in-memory for ORM tests (with PostgreSQL dialect awareness)
- Prioritize mocking actual PostgreSQL interface

---

## 11. Documentation

### In-Code
- Mandatory Google-style docstrings
- All public modules/classes/functions

### Project Docs
- `README.md`: Project overview
- `docs/architecture.md`: System design
- `docs/technical.md`: Technical details
- `docs/decisions.md`: Architecture decisions
- `docs/process.mmd`: Workflow diagrams

### PRDs
- Store in `docs/prds/`
- Track in `dewey.yaml`
- Regular updates

### Task Tracking
- `TODO.md`: Single source of truth
- Keep synchronized with code changes
