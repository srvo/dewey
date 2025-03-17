import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
import asyncio
from datetime import datetime

console = Console()

class PortCLI:
    def __init__(self):
        self.db = PortDatabase()
        self.console = Console()

    async def init(self):
        await self.db.init()

    @click.group()
    def cli():
        """Port Investment Research Platform"""
        pass

    @cli.command()
    @click.argument('ticker')
    @click.option('--type', '-t', default='research')
    @click.option('--tags', '-g', multiple=True)
    @click.option('--backup-only', is_flag=True, 
                  help="Write only to Supabase")
    async def note(self, ticker, type, tags, backup_only):
        """Add a research note with automatic backup"""
        content = click.edit()
        
        if content:
            with Progress() as progress:
                task = progress.add_task("Saving note...", total=2)
                
                if backup_only:
                    # Write directly to Supabase
                    result = self.db.supabase.table("research_notes").insert({
                        "ticker": ticker,
                        "content": content,
                        "note_type": type,
                        "tags": list(tags),
                        "created_by": "sloane@ethicic.com",
                        "created_at": datetime.utcnow().isoformat()
                    }).execute()
                    progress.update(task, advance=2)
                else:
                    # Write to both with primary DB first
                    pg_id, supabase_id = await self.db.add_note(
                        ticker, content, type, list(tags), 
                        "sloane@ethicic.com"
                    )
                    progress.update(task, advance=2)
                
                console.print("[green]Note saved successfully!")

    @cli.command()
    @click.option('--force', is_flag=True, 
                  help="Force sync all notes")
    async def sync(self, force):
        """Sync notes between primary DB and Supabase"""
        if force:
            # Full sync
            with Progress() as progress:
                task = progress.add_task("Syncing all notes...", total=100)
                await self.db.sync_all_notes(
                    lambda: progress.update(task, advance=1)
                )
        else:
            # Just sync missing
            await self.db.sync_missing_notes()
        
        console.print("[green]Sync completed!")

    @cli.command()
    @click.argument('ticker')
    @click.option('--source', type=click.Choice(['primary', 'backup', 'both']),
                  default='both')
    async def review(self, ticker, source):
        """Review notes from either/both databases"""
        table = Table(title=f"Research Notes - {ticker}")
        table.add_column("Date")
        table.add_column("Type")
        table.add_column("Content")
        table.add_column("Source")

        if source in ['primary', 'both']:
            async with self.db.pg_pool.acquire() as conn:
                notes = await conn.fetch("""
                    SELECT * FROM research_notes rn
                    JOIN companies c ON c.id = rn.company_id
                    WHERE c.ticker = $1
                    ORDER BY created_at DESC
                    """, ticker)
                
                for note in notes:
                    table.add_row(
                        note['created_at'].strftime("%Y-%m-%d %H:%M"),
                        note['note_type'],
                        note['content'][:100] + "...",
                        "Primary DB"
                    )

        if source in ['backup', 'both']:
            backup_notes = self.db.supabase.table("research_notes").select(
                "*"
            ).eq("ticker", ticker).execute()
            
            for note in backup_notes.data:
                table.add_row(
                    note['created_at'][:19],
                    note['note_type'],
                    note['content'][:100] + "...",
                    "Supabase"
                )

        console.print(table)

if __name__ == "__main__":
    cli = PortCLI()
    asyncio.run(cli.init())