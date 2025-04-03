# Dewey Project Structure

This document outlines the standardized project structure for the Dewey project as mandated by [CONVENTIONS.md](CONVENTIONS.md).

## Directory Structure

```
dewey/
├── src/
│   └── dewey/               # Main application source code
│       ├── __init__.py
│       ├── core/            # Core business logic modules
│       │   ├── __init__.py
│       │   ├── base_script.py # MANDATORY Base class for scripts
│       │   ├── config/      # Centralized configuration management
│       │   ├── db/          # Database access and connection management
│       │   ├── utils/       # Utility functions and helpers
│       │   ├── crm/         # CRM functionality
│       │   ├── research/    # Research tools and functionality
│       │   ├── bookkeeping/ # Financial and bookkeeping functionality
│       │   └── automation/  # Automation utilities
│       ├── llm/             # Language Model interactions
│       │   ├── __init__.py
│       │   ├── agents/      # LLM-based agents
│       │   ├── api_clients/ # Integration with LLM providers
│       │   └── prompts/     # Prompt templates and management
│       └── pipeline/        # Data processing pipeline stages
├── ui/                      # User Interface components
├── config/                  # Centralized configuration ONLY
│   └── dewey.yaml           # Primary configuration file
├── tests/                   # All test code
│   ├── conftest.py          # Root test configurations/fixtures
│   ├── unit/                # Unit tests (mirroring src structure)
│   │   ├── core/            # Tests for core functionality
│   │   ├── llm/             # Tests for LLM functionality
│   │   └── ...              # Other unit tests mirroring src structure
│   └── integration/         # Integration tests
│       ├── db/              # Database integration tests
│       ├── llm/             # LLM integration tests
│       └── ...              # Other integration tests
├── docs/                    # Documentation
├── scripts/                 # Utility/operational scripts
├── data/                    # Data storage
│   └── backups/             # Database and code backups
├── .env                     # Local environment variables (DO NOT COMMIT)
├── .env.example             # Example environment file
├── .gitignore
├── README.md                # Project overview, setup, core concepts
├── pyproject.toml           # Dependencies and project metadata
├── TODO.md                  # Central task tracking
└── .pre-commit-config.yaml  # Pre-commit hook configuration
```

## Key Principles

1. **Standardized Directory Structure**: All code follows the above directory structure exactly.
2. **BaseScript as Foundation**: All scripts inherit from `dewey.core.base_script.BaseScript`.
3. **Centralized Configuration**: All configuration is in `config/dewey.yaml`.
4. **Standardized Testing**: Tests mirror the source structure with clear unit vs integration separation.
5. **Data Storage**: All data files go in the `data/` directory with appropriate subdirectories.

## Configuration Management

Configuration is managed through the `ConfigManager` class in `src/dewey/core/config/__init__.py`, which extends `BaseScript`. This provides a standardized way to access configuration values and manage application settings.

## Migrating Code

When working with code in this project:

1. Place new modules in the appropriate directory based on functionality.
2. Ensure all scripts inherit from `BaseScript`.
3. Put tests in the corresponding unit or integration test directory.
4. Store data files in the `data/` directory.
5. Use `ConfigManager` for configuration access.

## Legacy Code

Some legacy directories like `backup/` and files directly in the `src/dewey` root have been migrated to follow this standardized structure. All new code must follow these conventions. 