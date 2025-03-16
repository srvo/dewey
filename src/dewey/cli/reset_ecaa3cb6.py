```python
import click

from ethifinx.core.logging_config import setup_logging
from ethifinx.db.data_store import DataStore

logger = setup_logging(__name__)


def confirm_reset() -> bool:
    """Confirms with the user if they want to reset the research data.

    Returns:
        bool: True if the user confirms, False otherwise.
    """
    if not click.confirm("This will delete all research data. Are you sure?"):
        click.echo("Operation cancelled.")
        return False
    return True


def reset_data() -> None:
    """Resets the research data using the DataStore."""
    try:
        data_store = DataStore()
        data_store.reset_research_data()
        logger.info("Successfully reset research data")
        click.echo("Research data has been reset.")
    except Exception as e:
        logger.error(f"Failed to reset research data: {e}")
        click.echo(f"Error: {str(e)}", err=True)


@click.command()
@click.option("--force", is_flag=True, help="Force reset without confirmation")
def reset_research(force: bool) -> None:
    """Resets all research data and checkpoints.

    Args:
        force (bool): If True, bypasses the confirmation prompt.
    """
    if not force:
        if not confirm_reset():
            return

    reset_data()


if __name__ == "__main__":
    reset_research()
```
