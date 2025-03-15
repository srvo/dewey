"""Vector database operations for code consolidation using ChromaDB."""
import logging
from typing import Optional
from pathlib import Path

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class VectorStore:
    """ChromaDB vector store for code embeddings."""
    
    def __init__(self, persist_dir: str = ".chroma_cache"):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(exist_ok=True)
        
        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=str(self.persist_dir)
        ))
        
        self.collection = self.client.get_or_create_collection("code_functions")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
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
            metadatas=[metadata]
        )
    
    def find_similar_functions(self, context: str, threshold: float = 0.85, top_k: int = 5) -> list[str]:
        """Find similar functions using vector similarity search."""
        query_embedding = self.generate_embedding(context)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["distances", "metadatas"]
        )
        
        return [
            result['id']
            for result, distance in zip(results['metadatas'][0], results['distances'][0])
            if distance < (1 - threshold)
        ]
    
    def persist(self) -> None:
        """Persist the database to disk."""
        self.client.persist()
