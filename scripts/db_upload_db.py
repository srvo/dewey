from dewey.core.db.operations import DatabaseMaintenance
from dewey.core.base_script import Config
import typer
from typing import Optional

app = typer.Typer()

@app.command()
def upload_db(
    db_name: str = typer.Argument(..., help="Database name to upload"),
    destination: str = typer.Option(..., "--destination", help="Upload destination"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate upload"),
    config_path: Optional[str] = typer.Option(None, help="Path to config file")
):
    """
    Upload database to specified destination
    """
    config = Config(config_path=config_path) if config_path else None
    maintenance = DatabaseMaintenance(config=config, dry_run=dry_run)
    
    if not db_name or not destination:
        typer.echo("Error: Database name and destination are required", err=True)
        raise typer.Exit(1)
        
    maintenance.upload_database(db_name, destination)

if __name__ == "__main__":
    app()
