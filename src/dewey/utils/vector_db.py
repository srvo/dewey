"""Vector database operations for code consolidation using ChromaDB."""

import logging
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class VectorStore:
    """ChromaDB vector store for code embeddings."""

    def __init__(
        self,
        persist_dir: str = ".chroma_cache",
        collection_name: str = "code_functions",
        embedding_model: str = "all-MiniLM-L6-v2",
        hnsw_config: dict | None = None,
        batch_size: int = 100,
        timeout: int = 30,
    ) -> None:
        """Initialize with HNSW configuration.
        
        Args:
            persist_dir: Directory to store vector DB
            collection_name: Name of collection to use
            embedding_model: Sentence transformer model name
            hnsw_config: HNSW configuration parameters
            batch_size: Number of items to process in batch operations
            timeout: Timeout in seconds for DB operations
        """
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(exist_ok=True)
        self.batch_size = batch_size
        self.timeout = timeout

        # Set default HNSW parameters
        self.hnsw_config = hnsw_config or {
            "hnsw:ef": 200,
            "hnsw:ef_construction": 300,
            "hnsw:M": 24,
        }

        # Initialize with timeout settings
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=chromadb.Settings(
                chroma_server_request_timeout_secs=self.timeout
            )
        )
        self.collection = self.client.get_or_create_collection(
            collection_name,
            metadata={"hnsw:space": "cosine"},  # Explicitly set similarity metric
        )
        self.embedding_model = SentenceTransformer(embedding_model)

        # Apply HNSW configuration
        self._apply_hnsw_settings()
        
        # Initialize metrics
        self.metrics = {
            "upsert_count": 0,
            "query_count": 0,
            "last_operation": None,
            "errors": []
        }

    def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for function context."""
        return self.embedding_model.encode(text).tolist()

    def upsert_function(self, function_id: str, context: str, metadata: dict) -> None:
        """Store or update function embedding with timeout and error handling."""
        try:
            embedding = self.generate_embedding(context)
            self.collection.upsert(
                ids=[function_id],
                embeddings=[embedding],
                documents=[context],
                metadatas=[metadata],
                timeout=self.timeout
            )
            self.metrics["upsert_count"] += 1
            self.metrics["last_operation"] = "upsert"
        except Exception as e:
            self.metrics["errors"].append({
                "operation": "upsert",
                "function_id": function_id,
                "error": str(e)
            })
            logger.error(f"Failed to upsert {function_id}: {e}")

    def _apply_hnsw_settings(self) -> None:
        """Update collection with current HNSW config."""
        try:
            self.collection.modify(metadata=self.hnsw_config)
        except Exception as e:
            logger.warning(f"Couldn't update HNSW settings: {e}")

    def find_similar_functions(
        self,
        context: str,
        threshold: float = 0.85,
        top_k: int = 5,
        ef: int | None = None,
    ) -> list[str]:
        """Find similar functions with adjustable ef parameter and timeout."""
        try:
            query_embedding = self.generate_embedding(context)
            collection_count = self.collection.count()

            if collection_count == 0:
                return []

            safe_top_k = min(top_k, collection_count)
            query_params = {"ef": ef} if ef else {}

            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=safe_top_k,
                include=["distances", "metadatas"],
                timeout=self.timeout,
                **query_params,
            )
            
            self.metrics["query_count"] += 1
            self.metrics["last_operation"] = "query"

            return [
                result_id
                for result_id, distance in zip(
                    results["ids"][0], results["distances"][0], strict=False
                )
                if distance < (1 - threshold)
            ]
        except RuntimeError as e:
            if "contigious 2D array" in str(e):
                logger.warning("HNSW dimension error - retrying with higher ef=500")
                return self.find_similar_functions(context, threshold, top_k, ef=500)
            self.metrics["errors"].append({
                "operation": "query",
                "context": context[:100],
                "error": str(e)
            })
            logger.error(f"Query failed: {e}")
            return []

    def persist(self) -> None:
        """Persist the database to disk with timeout."""
        try:
            self.client.persist(timeout=self.timeout)
            logger.info("Vector DB persisted successfully")
        except Exception as e:
            self.metrics["errors"].append({
                "operation": "persist",
                "error": str(e)
            })
            logger.error(f"Failed to persist vector DB: {e}")

    def get_metrics(self) -> dict:
        """Get current performance metrics.
        
        Returns:
            Dictionary containing:
            - upsert_count: Number of upsert operations
            - query_count: Number of queries
            - last_operation: Last operation performed
            - errors: List of recent errors
        """
        return self.metrics
