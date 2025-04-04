from dewey.core.db.operations import DatabaseMaintenance
from dewey.core.base_script import Config
import typer

app = typer.Typer()

@app.command()
def force_cleanup(
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate cleanup"),
    config_path: str = typer.Option(None, help="Path to config file")
):
    """
    Force cleanup of database objects (tables, indexes, etc.)
    """
    config = Config(config_path=config_path) if config_path else None
    maintenance = DatabaseMaintenance(config=config, dry_run=dry_run)
    
    # Add force cleanup logic to DatabaseMaintenance class
    maintenance.force_cleanup()

if __name__ == "__main__":
    app()
