"""
Database CLI commands.

Provides command-line interface for database operations using Typer.
"""

import typer
from typing import Optional, List
from dewey.core.db.operations import DatabaseMaintenance
from dewey.core.base_script import Config

app = typer.Typer(help="Database operations")

@app.command()
def cleanup_tables(
    tables: List[str] = typer.Argument(..., help="Tables to clean"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate cleanup without making changes"),
    config_path: Optional[str] = typer.Option(None, help="Path to config file")
):
    """
    Clean up data in specified tables.
    """
    config = Config(config_path=config_path) if config_path else None
    maintenance = DatabaseMaintenance(config=config, dry_run=dry_run)
    maintenance.cleanup_tables(tables)

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

@app.command()
def force_cleanup(
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate cleanup"),
    config_path: Optional[str] = typer.Option(None, help="Path to config file")
):
    """
    Force cleanup of all database objects (tables, indexes, etc.)
    """
    config = Config(config_path=config_path) if config_path else None
    maintenance = DatabaseMaintenance(config=config, dry_run=dry_run)
    maintenance.force_cleanup()

@app.command()
def analyze_tables(
    tables: List[str] = typer.Argument(..., help="Tables to analyze"),
    config_path: Optional[str] = typer.Option(None, help="Path to config file")
):
    """
    Analyze tables and display statistics.
    """
    config = Config(config_path=config_path) if config_path else None
    maintenance = DatabaseMaintenance(config=config)
    results = maintenance.analyze_tables(tables)
    
    for table, stats in results.items():
        typer.echo(f"{table}:")
        typer.echo(f"  Rows: {stats['row_count']}")
        typer.echo(f"  Size: {stats['size_bytes']} bytes")
        typer.echo()

if __name__ == "__main__":
    app()