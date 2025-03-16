"""RAG agent for semantic search using pgvector."""

from __future__ import annotations

import json
from dataclasses import dataclass

import asyncpg
import structlog
from pydantic import BaseModel, Field

from ..base import FunctionDefinition, SyzygyAgent

logger = structlog.get_logger(__name__)

# Schema for our knowledge base
KNOWLEDGE_SCHEMA = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS knowledge_base (
    id SERIAL PRIMARY KEY,
    content_type TEXT NOT NULL,  -- email, contact, document, etc.
    title TEXT,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    embedding vector(1536) NOT NULL,  -- Using 1536d embeddings from DeepInfra
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create HNSW index for fast similarity search
CREATE INDEX IF NOT EXISTS idx_knowledge_base_embedding
ON knowledge_base
USING hnsw (embedding vector_l2_ops);

-- Index on content type for filtering
CREATE INDEX IF NOT EXISTS idx_knowledge_base_content_type
ON knowledge_base (content_type);
"""


@dataclass
class DatabaseConnection:
    """Database connection for RAG operations."""

    pool: asyncpg.Pool


class SearchResult(BaseModel):
    """A single search result from the knowledge base."""

    content_type: str
    title: str | None
    content: str
    similarity: float
    metadata: dict = Field(default_factory=dict)


class RAGAgent(SyzygyAgent):
    """DEPRECATED: RAG agent for semantic search using pgvector.

    This agent is deprecated and should only be used for testing purposes.
    New implementations should use the external workflow integration library.
    """

    def __init__(self) -> None:
        """Initialize the DEPRECATED RAG agent."""
        logger.warning(
            "RAGAgent is deprecated - use external workflow integration instead",
        )
        super().__init__(
            task_type="rag_search",
            model="mistral-7b-instruct",
            deprecated=True,  # Add deprecated flag
            functions=[
                FunctionDefinition(
                    name="semantic_search",
                    description="Search the knowledge base using semantic similarity",
                    parameters={
                        "query": {"type": "string", "description": "The search query"},
                        "content_type": {
                            "type": "string",
                            "description": "Optional content type filter",
                        },
                        "limit": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 10,
                            "description": "Maximum number of results",
                        },
                    },
                    required=["query"],
                ),
            ],
        )

    def get_system_prompt(self) -> str:
        """Get the system prompt for the RAG agent."""
        return """You are an expert search agent in the Syzygy system, responsible for finding relevant information in the knowledge base.

Your role is to:
1. Understand the user's query intent
2. Formulate effective semantic search queries
3. Filter and rank results by relevance
4. Provide clear explanations of found information

Key guidelines:
- Focus on semantic meaning over keyword matching
- Consider context and relationships
- Explain why results are relevant
- Be clear about confidence levels
- Indicate when information might be incomplete

Use the semantic_search function to find relevant information."""

    async def initialize_db(self, conn_str: str) -> None:
        """Initialize the database with required schema.

        Args:
        ----
            conn_str: PostgreSQL connection string

        """
        # Create initial connection to create database if needed
        system_conn = await asyncpg.connect(conn_str)
        try:
            # Check if database exists
            db_name = "syzygy_knowledge"
            exists = await system_conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1",
                db_name,
            )

            if not exists:
                await system_conn.execute(f"CREATE DATABASE {db_name}")

        finally:
            await system_conn.close()

        # Connect to specific database and create schema
        db_conn = await asyncpg.connect(f"{conn_str}/{db_name}")
        try:
            await db_conn.execute(KNOWLEDGE_SCHEMA)
        finally:
            await db_conn.close()

    async def add_to_knowledge_base(
        self,
        pool: asyncpg.Pool,
        content: str,
        content_type: str,
        title: str | None = None,
        metadata: dict | None = None,
    ) -> int:
        """Add content to the knowledge base with embeddings.

        Args:
        ----
            pool: Database connection pool
            content: The content to add
            content_type: Type of content
            title: Optional title
            metadata: Optional metadata

        Returns:
        -------
            ID of the created entry

        """
        # Get embedding from DeepInfra
        embedding_result = await self.run(
            prompt=content,
            model="mistral-7b-instruct",  # Use basic model for embeddings
            operation="generate_embedding",
        )

        embedding = embedding_result.get("embedding", [])
        if not embedding:
            msg = "Failed to generate embedding"
            raise ValueError(msg)

        # Insert into database
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO knowledge_base (content_type, title, content, metadata, embedding)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
                """,
                content_type,
                title,
                content,
                json.dumps(metadata or {}),
                embedding,
            )

        return row["id"]

    async def search(
        self,
        pool: asyncpg.Pool,
        query: str,
        content_type: str | None = None,
        limit: int = 5,
    ) -> list[SearchResult]:
        """Search the knowledge base using semantic similarity.

        Args:
        ----
            pool: Database connection pool
            query: Search query
            content_type: Optional content type filter
            limit: Maximum number of results

        Returns:
        -------
            List of search results

        """
        # Get query embedding
        embedding_result = await self.run(
            prompt=query,
            model="mistral-7b-instruct",
            operation="generate_embedding",
        )

        embedding = embedding_result.get("embedding", [])
        if not embedding:
            msg = "Failed to generate query embedding"
            raise ValueError(msg)

        # Build query
        query = """
        SELECT
            content_type,
            title,
            content,
            metadata,
            1 - (embedding <=> $1::vector) as similarity
        FROM knowledge_base
        """

        params = [json.dumps(embedding)]
        if content_type:
            query += " WHERE content_type = $2"
            params.append(content_type)

        query += """
        ORDER BY embedding <=> $1::vector
        LIMIT $%d
        """ % (
            len(params) + 1
        )
        params.append(limit)

        # Execute search
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [
            SearchResult(
                content_type=row["content_type"],
                title=row["title"],
                content=row["content"],
                similarity=row["similarity"],
                metadata=row["metadata"],
            )
            for row in rows
        ]

    async def answer_with_context(
        self,
        pool: asyncpg.Pool,
        question: str,
        content_type: str | None = None,
    ) -> str:
        """Answer a question using retrieved context.

        Args:
        ----
            pool: Database connection pool
            question: The question to answer
            content_type: Optional content type filter

        Returns:
        -------
            Answer with supporting context

        """
        # Search for relevant context
        results = await self.search(pool, question, content_type)

        if not results:
            return "I couldn't find any relevant information to answer your question."

        # Prepare context from results
        context = "\n\n".join(
            f"[{r.content_type}] {r.title or 'Untitled'}\n{r.content}" for r in results
        )

        # Get answer using context
        prompt = f"""Based on the following context, please answer this question: {question}

Context:
{context}

Please provide a clear answer, citing specific information from the context where relevant."""

        result = await self.run(
            prompt=prompt,
            model="mixtral-8x7b",  # Use more capable model for synthesis
            metadata={"context_count": len(results)},
        )

        return result["content"] if isinstance(result, dict) else result
