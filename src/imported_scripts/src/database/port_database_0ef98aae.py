import os
from datetime import datetime

import asyncpg
from supabase import create_client


class PortDatabase:
    def __init__(self) -> None:
        # Primary PostgreSQL connection
        self.pg_pool = None

        # Supabase client
        self.supabase = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY"),
        )

    async def init(self) -> None:
        self.pg_pool = await asyncpg.create_pool(
            os.getenv("DATABASE_URL"),
            min_size=3,
            max_size=10,
        )

    async def add_note(
        self,
        ticker: str,
        content: str,
        note_type: str,
        tags: list[str],
        user: str,
    ) -> tuple[int, int]:
        """Add note to both primary DB and Supabase
        Returns (pg_id, supabase_id).
        """
        # First, write to primary DB
        async with self.pg_pool.acquire() as conn:
            pg_id = await conn.fetchval(
                """
                WITH company_id AS (
                    SELECT id FROM companies WHERE ticker = $1
                )
                INSERT INTO research_notes (
                    company_id, content, note_type,
                    created_by, tags, created_at
                )
                SELECT
                    company_id.id, $2, $3, $4, $5, $6
                FROM company_id
                RETURNING id
                """,
                ticker,
                content,
                note_type,
                user,
                tags,
                datetime.utcnow(),
            )

        # Then sync to Supabase
        supabase_data = {
            "pg_id": pg_id,
            "ticker": ticker,
            "content": content,
            "note_type": note_type,
            "created_by": user,
            "tags": tags,
            "created_at": datetime.utcnow().isoformat(),
        }

        result = self.supabase.table("research_notes").insert(supabase_data).execute()

        return pg_id, result.data[0]["id"]

    async def sync_missing_notes(self) -> None:
        """Sync any notes that might have failed to replicate."""
        async with self.pg_pool.acquire() as conn:
            pg_notes = await conn.fetch(
                """
                SELECT id, company_id, content, note_type,
                       created_by, tags, created_at
                FROM research_notes
                WHERE synced_to_supabase = false
                ORDER BY created_at DESC
                LIMIT 100
            """,
            )

        for note in pg_notes:
            try:
                result = (
                    self.supabase.table("research_notes")
                    .insert(
                        {
                            "pg_id": note["id"],
                            "content": note["content"],
                            "note_type": note["note_type"],
                            "created_by": note["created_by"],
                            "tags": note["tags"],
                            "created_at": note["created_at"].isoformat(),
                        },
                    )
                    .execute()
                )

                # Mark as synced in primary DB
                async with self.pg_pool.acquire() as conn:
                    await conn.execute(
                        """
                        UPDATE research_notes
                        SET synced_to_supabase = true,
                            supabase_id = $2
                        WHERE id = $1
                        """,
                        note["id"],
                        result.data[0]["id"],
                    )
            except Exception:
                pass
