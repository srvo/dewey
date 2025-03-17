"""Database migration management using Alembic.

This module provides a programmatic interface to run Alembic commands
for database schema migrations. It acts as a wrapper around Alembic's
command-line interface, allowing migrations to be executed from within
the application code or as a script.

Typical usage:
    python manage_migrations.py [command] [options]

Supported commands include:
    - upgrade: Apply migrations to upgrade database schema
    - downgrade: Revert migrations to downgrade schema
    - revision: Create new migration scripts
    - current: Show current revision
    - history: Show migration history
    - stamp: Stamp database with specific revision
"""

import os
import sys
from typing import Any, List

from alembic import command
from alembic.config import Config


def run_alembic_command(command_name: str) -> None:
    """Execute an Alembic command with provided arguments.

    Args:
    ----
        command_name (str): Name of the Alembic command to execute.
            Must be a valid Alembic command like 'upgrade', 'downgrade', etc.

    Raises:
    ------
        AttributeError: If the command_name is not a valid Alembic command.
        Exception: Any errors from the underlying Alembic command execution.

    """
    # Load Alembic configuration from alembic.ini file
    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))

    # Get additional command arguments from sys.argv
    command_args: List[Any] = sys.argv[2:]

    # Dynamically get and execute the Alembic command
    try:
        getattr(command, command_name)(alembic_cfg, *command_args)
    except AttributeError as e:
        raise AttributeError(f"Invalid Alembic command: {command_name}") from e


if __name__ == "__main__":
    # Basic command-line argument validation
    if len(sys.argv) < 2:
        print("Usage: python manage_migrations.py [command] [options]")
        print(
            "Available commands: upgrade, downgrade, revision, current, history, stamp"
        )
        sys.exit(1)

    # Extract and execute the requested command
    cmd: str = sys.argv[1]
    try:
        run_alembic_command(cmd)
    except Exception as e:
        print(f"Error executing migration command: {e}")
        sys.exit(1)
