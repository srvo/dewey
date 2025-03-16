from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import aiosqlite


class DatabaseManager:
    def __init__(self, db_path: str = "api_manager.db") -> None:
        self.db_path = db_path
        self._initialized = False

    async def ensure_initialized(self) -> None:
        """Ensure the database is initialized."""
        if not self._initialized:
            await self._init_db()
            self._initialized = True

    async def _init_db(self) -> None:
        """Initialize SQLite database with necessary tables."""
        async with aiosqlite.connect(self.db_path) as db:
            # Drop existing tables if they exist
            await db.execute("DROP TABLE IF EXISTS api_calls")
            await db.execute("DROP TABLE IF EXISTS api_usage")

            # Table for storing API call history
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS api_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint TEXT NOT NULL,
                    request_data TEXT,
                    response_data TEXT,
                    response_status INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """,
            )

            # Table for tracking API usage
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS api_usage (
                    endpoint TEXT NOT NULL,
                    date TEXT NOT NULL,
                    count INTEGER DEFAULT 0,
                    PRIMARY KEY (endpoint, date)
                )
            """,
            )

            await db.commit()

    async def log_api_call(
        self,
        endpoint: str,
        request_data: str,
        response_data: str,
        response_status: int,
    ) -> None:
        """Log an API call to the database."""
        await self.ensure_initialized()
        async with aiosqlite.connect(self.db_path) as db:
            # Log the API call
            await db.execute(
                """INSERT INTO api_calls
                   (endpoint, request_data, response_data, response_status)
                   VALUES (?, ?, ?, ?)""",
                (endpoint, request_data, response_data, response_status),
            )

            # Update usage count only for successful calls
            if response_status == 200:
                today = datetime.now().date().isoformat()
                await db.execute(
                    """INSERT INTO api_usage (endpoint, date, count)
                       VALUES (?, ?, 1)
                       ON CONFLICT(endpoint, date)
                       DO UPDATE SET count = count + 1""",
                    (endpoint, today),
                )

            await db.commit()

    async def get_api_usage(
        self,
        endpoint: str | None = None,
        since: datetime | None = None,
    ) -> dict[str, int]:
        """Get API usage statistics."""
        await self.ensure_initialized()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # Calculate date range
            end_date = datetime.now().date()
            start_date = since.date() if since else (end_date - timedelta(days=1))

            query = """
                SELECT endpoint, SUM(count) as count
                FROM api_usage
                WHERE date >= ? AND date <= ?
            """
            params = [start_date.isoformat(), end_date.isoformat()]

            if endpoint:
                query += " AND endpoint = ?"
                params.append(endpoint)

            query += " GROUP BY endpoint"

            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                if endpoint:
                    # Return count for specific endpoint
                    return {endpoint: rows[0]["count"] if rows else 0}
                # Return counts for all endpoints
                return {row["endpoint"]: row["count"] for row in rows}

    async def get_recent_calls(self, limit: int = 5) -> list[dict[str, Any]]:
        """Get recent API calls."""
        await self.ensure_initialized()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            query = """
                SELECT *
                FROM api_calls
                ORDER BY timestamp DESC
                LIMIT ?
            """

            async with db.execute(query, [limit]) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def cleanup_old_data(self, days: int = 30) -> None:
        """Clean up API call records older than specified days."""
        await self.ensure_initialized()
        async with aiosqlite.connect(self.db_path) as db:
            cutoff_date = (datetime.now() - timedelta(days=days)).date()

            # Clean up old API calls
            await db.execute(
                "DELETE FROM api_calls WHERE date(timestamp) < ?",
                (cutoff_date.isoformat(),),
            )

            # Clean up old usage data
            await db.execute(
                "DELETE FROM api_usage WHERE date < ?",
                (cutoff_date.isoformat(),),
            )

            await db.commit()
