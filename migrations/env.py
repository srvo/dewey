import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Create rich console instance
console = Console()

# Add project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# Import your SQLAlchemy Base and models
from dewey.core.db.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_online() -> None:
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console
    ) as progress:
        progress.add_task("Initializing database connection...", total=None)
        
        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

        with connectable.connect() as connection:
            progress.add_task("Configuring migration context...", total=None)
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
                compare_server_default=True,
                process_revision_directives=lambda a, b, c: console.log(
                    f"Processing revision directives for [bold]{', '.join(r.revision for r in c)}[/]",
                    style="dim"
                )
            )

            with context.begin_transaction():
                progress.add_task("Running migrations...", total=None)
                context.run_migrations()
                
    console.print("[bold green]✓ Migrations completed successfully[/]")

if __name__ == "__main__":
    from rich.prompt import Confirm
    
    if Confirm.ask("[bold yellow]Apply database migrations?[/]", default=False):
        run_migrations_online()
    else:
        console.print("[bold red]× Migration cancelled[/]")
