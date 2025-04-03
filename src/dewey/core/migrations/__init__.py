"""
Migrations module for the Dewey project.

This module provides functionality for managing database migrations, including:
- Running migrations
- Creating new migrations
- Tracking applied migrations
"""

from dewey.core.migrations.migration_manager import MigrationManager

__all__ = ["MigrationManager"] 