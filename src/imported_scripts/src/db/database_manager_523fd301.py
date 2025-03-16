from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import aiosqlite


class DatabaseManager:
    """Manages an SQLite database for logging API calls and tracking usage."""

    def __init__(self, db_path: str = "api_manager.db") -> None:
        """Initializes the DatabaseManager with the specified database path.

        Args:
            db_path: The path to the SQLite database file.

        """
        self.db_path = db_path
        self._initialized = False

    async def ensure_initialized(self) -> None:
        """Ensures that the database is initialized."""
        if not self._initialized:
            await self._init_db()
            self._initialized = True

    async def _init_db(self) -> None:
        """Initializes the SQLite database with the necessary tables."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DROP TABLE IF EXISTS api_calls")
            await db.execute("DROP TABLE IF EXISTS api_usage")

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
        """Logs an API call to the database.

        Args:
            endpoint: The API endpoint that was called.
            request_data: The data sent in the request.
            response_data: The data received in the response.
            response_status: The HTTP status code of the response.

        """
        await self.ensure_initialized()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO api_calls
                   (endpoint, request_data, response_data, response_status)
                   VALUES (?, ?, ?, ?)""",
                (endpoint, request_data, response_data, response_status),
            )

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
        """Gets API usage statistics.

        Args:
            endpoint: An optional API endpoint to filter by.
            since: An optional datetime to filter usage since.

        Returns:
            A dictionary containing API usage statistics.

        """
        await self.ensure_initialized()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

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
                    return {endpoint: rows[0]["count"] if rows else 0}
                return {row["endpoint"]: row["count"] for row in rows}

    async def get_recent_calls(self, limit: int = 5) -> list[dict[str, Any]]:
        """Gets recent API calls.

        Args:
            limit: The maximum number of recent calls to retrieve.

        Returns:
            A list of dictionaries, each representing a recent API call.

        """
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
        """Cleans up API call records older than the specified number of days.

        Args:
            days: The number of days to retain API call records for.

        """
        await self.ensure_initialized()
        async with aiosqlite.connect(self.db_path) as db:
            cutoff_date = (datetime.now() - timedelta(days=days)).date()

            await db.execute(
                "DELETE FROM api_calls WHERE date(timestamp) < ?",
                (cutoff_date.isoformat(),),
            )

            await db.execute(
                "DELETE FROM api_usage WHERE date < ?",
                (cutoff_date.isoformat(),),
            )

            await db.commit()
