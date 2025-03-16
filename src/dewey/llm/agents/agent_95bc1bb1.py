# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:53:33 2025

"""RAG agent for semantic search using pgvector."""
from .rag_agent import RAGAgent  # Import the new agent

async def search(query: str, content_type: str | None = None, limit: int = 5) -> str:
    """Searches the knowledge base using semantic similarity using the new RAGAgent."""
    agent = RAGAgent()
    return await agent.search(query, content_type, limit)
