import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from models.tick_history import Base, get_engine

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This function configures and runs Alembic migrations against a database
    specified by the 'sqlalchemy.url' configuration option, without establishing
    a direct connection.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def configure_and_run_migrations(connection: Connection) -> None:
    """Configures and runs Alembic migrations within a transaction.

    Args:
    ----
        connection: The SQLAlchemy connection to use for the migration.

    """
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    This function establishes a connection to the database, configures Alembic
    to use this connection, and then runs the migrations within a transaction.
    """
    # Use SQLite for migrations
    connectable = get_engine(use_sqlite=True)

    with connectable.connect() as connection:
        configure_and_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
