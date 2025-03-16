"""RAG agent for semantic search using pgvector (DEPRECATED)."""
from typing import List, Dict, Any, Optional
import structlog
from smolagents import Tool
from .base_agent import DeweyBaseAgent

logger = structlog.get_logger(__name__)

class RAGAgent(DeweyBaseAgent):
    """DEPRECATED: RAG agent for semantic search. Use external workflow integration instead.
    
    Attributes:
        task_type: The type of task the agent performs (rag_search)
    """

    def __init__(self) -> None:
        """Initializes the RAGAgent and logs deprecation warning."""
        super().__init__(task_type="rag_search")
        logger.warning("RAGAgent is deprecated - use external workflow integration instead")
        self.add_tools([
            Tool.from_function(self.search, description="Searches the knowledge base using semantic similarity.")
        ])

    def search(self, query: str, content_type: Optional[str] = None, limit: int = 5) -> str:
        """
        Searches the knowledge base using semantic similarity.

        Args:
            query (str): The search query.
            content_type (Optional[str], optional): Content type filter. Defaults to None.
            limit (int, optional): Maximum number of results. Defaults to 5.

        Returns:
            str: The search results.
        """
        prompt = f"""
        Search the knowledge base for: {query}
        Content Type: {content_type or "any"}
        Limit: {limit}
        """
        result = self.run(prompt)
        return result
