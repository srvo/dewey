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
    ) -> None:
        """Initialize with HNSW configuration."""
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(exist_ok=True)
        
        # Set default HNSW parameters
        self.hnsw_config = hnsw_config or {
            "hnsw:ef": 200,
            "hnsw:ef_construction": 300,
            "hnsw:M": 24,
        }

        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        self.collection = self.client.get_or_create_collection(
            collection_name,
            metadata={"hnsw:space": "cosine"},  # Explicitly set similarity metric
        )
        self.embedding_model = SentenceTransformer(embedding_model)
        
        # Apply HNSW configuration
        self._apply_hnsw_settings()

    def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for function context."""
        return self.embedding_model.encode(text).tolist()

    def upsert_function(self, function_id: str, context: str, metadata: dict) -> None:
        """Store or update function embedding."""
        embedding = self.generate_embedding(context)
        self.collection.upsert(
            ids=[function_id],
            embeddings=[embedding],
            documents=[context],
            metadatas=[metadata],
        )

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
        """Find similar functions with adjustable ef parameter."""
        query_embedding = self.generate_embedding(context)
        collection_count = self.collection.count()
        
        if collection_count == 0:
            return []

        safe_top_k = min(top_k, collection_count)
        query_params = {"ef": ef} if ef else {}

        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=safe_top_k,
                include=["distances", "metadatas"],
                **query_params,
            )
        except RuntimeError as e:
            if "contigious 2D array" in str(e):
                logger.warning("HNSW dimension error - retrying with higher ef=500")
                return self.find_similar_functions(context, threshold, top_k, ef=500)
            raise

        return [
            result_id
            for result_id, distance in zip(results["ids"][0], results["distances"][0], strict=False)
            if distance < (1 - threshold)
        ]

    def persist(self) -> None:
        """Persist the database to disk."""
        self.client.persist()
