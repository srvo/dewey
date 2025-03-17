import click

from ethifinx.core.logging_config import setup_logging
from ethifinx.db.data_store import DataStore

logger = setup_logging(__name__)


@click.command()
@click.option("--force", is_flag=True, help="Force reset without confirmation")
def reset_research(force: bool):
    """Reset all research data and checkpoints."""
    if not force:
        if not click.confirm("This will delete all research data. Are you sure?"):
            click.echo("Operation cancelled.")
            return

    try:
        data_store = DataStore()
        data_store.reset_research_data()
        logger.info("Successfully reset research data")
        click.echo("Research data has been reset.")
    except Exception as e:
        logger.error(f"Failed to reset research data: {e}")
        click.echo(f"Error: {str(e)}", err=True)


if __name__ == "__main__":
    reset_research()
