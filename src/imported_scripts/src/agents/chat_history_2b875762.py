"""Chat history management for AI agents with PostgreSQL persistence."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any

import structlog
from pydantic import BaseModel, Field
from pydantic_ai import Message, Role

from ..base import SyzygyAgent

if TYPE_CHECKING:
    import asyncpg

logger = structlog.get_logger(__name__)

CHAT_SCHEMA = """
CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    role TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    embedding vector(1536),
    conversation_id TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation
ON chat_messages (conversation_id);

CREATE INDEX IF NOT EXISTS idx_chat_messages_embedding
USING hnsw (embedding vector_l2_ops)
WHERE embedding IS NOT NULL;
"""


class ChatMessage(BaseModel):
    """A single message in the chat history."""

    content: str
    role: Role
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)
    conversation_id: str


class ChatContext(BaseModel):
    """Context extracted from chat history."""

    summary: str
    key_points: list[str]
    entities: dict[str, Any]
    last_action: str | None = None
    confidence: float


class ChatHistoryAgent(SyzygyAgent):
    """Agent for managing chat history and context.

    Features:
    - Maintains conversation history in PostgreSQL
    - Provides relevant context to other agents
    - Summarizes key points and entities
    - Tracks conversation state
    - Semantic search across chat history
    """

    def __init__(self, pool: asyncpg.Pool, conversation_id: str) -> None:
        """Initialize the chat history agent.

        Args:
            pool: Database connection pool
            conversation_id: Unique identifier for this conversation

        """
        super().__init__(
            task_type="chat_history",
            model="mistral-7b-instruct",  # Start with basic model
        )
        self.pool = pool
        self.conversation_id = conversation_id

    async def initialize_db(self) -> None:
        """Initialize the database schema."""
        async with self.pool.acquire() as conn:
            await conn.execute(CHAT_SCHEMA)

    async def add_message(
        self,
        content: str,
        role: Role,
        metadata: dict | None = None,
    ) -> None:
        """Add a message to the history.

        Args:
            content: Message content
            role: Message role (user/assistant/system)
            metadata: Optional metadata about the message

        """
        # Generate embedding for semantic search
        embedding_result = await self.run(
            prompt=content,
            model="mistral-7b-instruct",
            operation="generate_embedding",
        )

        embedding = embedding_result.get("embedding", None)

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO chat_messages
                (content, role, metadata, embedding, conversation_id)
                VALUES ($1, $2, $3, $4, $5)
                """,
                content,
                role.value,
                json.dumps(metadata or {}),
                embedding,
                self.conversation_id,
            )

    async def get_messages(
        self,
        limit: int | None = None,
        before: datetime | None = None,
    ) -> list[ChatMessage]:
        """Get messages from history.

        Args:
            limit: Optional maximum number of messages
            before: Optional timestamp to get messages before

        Returns:
            List of messages

        """
        query = """
        SELECT content, role, timestamp, metadata, conversation_id
        FROM chat_messages
        WHERE conversation_id = $1
        """
        params = [self.conversation_id]

        if before:
            query += " AND timestamp < $2"
            params.append(before)

        query += " ORDER BY timestamp DESC"

        if limit:
            query += f" LIMIT {limit}"

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [
            ChatMessage(
                content=row["content"],
                role=Role(row["role"]),
                timestamp=row["timestamp"],
                metadata=row["metadata"],
                conversation_id=row["conversation_id"],
            )
            for row in rows
        ]

    async def get_context(self, query: str | None = None) -> ChatContext:
        """Get relevant context from chat history.

        Args:
            query: Optional query to focus context extraction

        Returns:
            Extracted context from relevant messages

        """
        # Get recent messages
        messages = await self.get_messages(limit=10)

        # If query provided, also get semantically similar messages
        if query:
            embedding_result = await self.run(
                prompt=query,
                model="mistral-7b-instruct",
                operation="generate_embedding",
            )

            if embedding := embedding_result.get("embedding"):
                async with self.pool.acquire() as conn:
                    similar_rows = await conn.fetch(
                        """
                        SELECT content, role, timestamp, metadata
                        FROM chat_messages
                        WHERE conversation_id = $1
                        AND embedding IS NOT NULL
                        ORDER BY embedding <=> $2::vector
                        LIMIT 5
                        """,
                        self.conversation_id,
                        embedding,
                    )

                    messages.extend(
                        [
                            ChatMessage(
                                content=row["content"],
                                role=Role(row["role"]),
                                timestamp=row["timestamp"],
                                metadata=row["metadata"],
                                conversation_id=self.conversation_id,
                            )
                            for row in similar_rows
                        ],
                    )

        # Convert to PydanticAI format
        history = [Message(content=msg.content, role=msg.role) for msg in messages]

        # Get context using more capable model
        result = await self.run(
            messages=history,
            model="mixtral-8x7b",
            metadata={"query": query} if query else {},
            operation="extract_context",
        )

        return ChatContext(
            summary=result["summary"],
            key_points=result["key_points"],
            entities=result["entities"],
            last_action=result.get("last_action"),
            confidence=result["confidence"],
        )

    async def search_history(self, query: str, limit: int = 5) -> list[ChatMessage]:
        """Search chat history using semantic similarity.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of relevant messages

        """
        embedding_result = await self.run(
            prompt=query,
            model="mistral-7b-instruct",
            operation="generate_embedding",
        )

        if not (embedding := embedding_result.get("embedding")):
            return []

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT content, role, timestamp, metadata
                FROM chat_messages
                WHERE conversation_id = $1
                AND embedding IS NOT NULL
                ORDER BY embedding <=> $2::vector
                LIMIT $3
                """,
                self.conversation_id,
                embedding,
                limit,
            )

        return [
            ChatMessage(
                content=row["content"],
                role=Role(row["role"]),
                timestamp=row["timestamp"],
                metadata=row["metadata"],
                conversation_id=self.conversation_id,
            )
            for row in rows
        ]

    async def summarize_conversation(self) -> str:
        """Generate a summary of the entire conversation.

        Returns:
            Conversation summary

        """
        messages = await self.get_messages()

        if not messages:
            return "No conversation history available."

        history = [Message(content=msg.content, role=msg.role) for msg in messages]

        result = await self.run(
            messages=history,
            model="mixtral-8x7b",
            operation="summarize_conversation",
        )

        return result["summary"] if isinstance(result, dict) else result

    async def clear_history(self) -> None:
        """Clear the conversation history."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM chat_messages WHERE conversation_id = $1",
                self.conversation_id,
            )
