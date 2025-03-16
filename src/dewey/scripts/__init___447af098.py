# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:47:41 2025

"""Scripts package for email processing and automation.

This package contains modules for handling various aspects of email processing,
including database operations, message fetching, analysis, and automation workflows.

The package is organized into several key functional areas:
- Database connectivity and management (db_connector, db_maintenance)
- Email fetching and processing (fetch_messages, email_service)
- Analysis and rule execution (email_analyzer, rule_engine)
- Utility and support functions (log_manager, config)

Each module is designed to be independently usable while integrating seamlessly
with the rest of the package through well-defined interfaces.
"""

__version__ = "0.1.0"
"""Current version of the scripts package.

Follows semantic versioning (MAJOR.MINOR.PATCH) where:
- MAJOR version indicates incompatible API changes
- MINOR version indicates added functionality in a backward-compatible manner
- PATCH version indicates backward-compatible bug fixes
"""

__all__ = [
    "db_connector",  # Database connection management and operations
    "fetch_messages",  # Core email fetching and processing functionality
    # Add other module names here with brief descriptions
    # Example:
    # "email_analyzer",  # Email content analysis and classification
    # "rule_engine",     # Rule-based email processing engine
]
"""List of public modules that should be imported when using 'from scripts import *'.

This controls which modules are exposed as part of the public API. Only well-tested
and stable modules should be included here. Internal implementation details should
be kept private by omitting them from this list.

Note: Explicit imports are generally preferred over wildcard imports for better
code clarity and to avoid namespace pollution.
"""
