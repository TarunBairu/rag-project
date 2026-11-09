import logging
from typing import Any, Dict, List, Optional

from app.config.settings import get_settings
from app.embeddings.embedder import BaseEmbedder, get_embedder
from app.vectorstore.vector_db import VectorDB, get_vector_db

logger = logging.getLogger("rag.retriever")
settings = get_settings()


class RAGRetriever:
    """Retrieves relevant document chunks using vector similarity."""

    def __init__(
        self,
        embedder: Optional[BaseEmbedder] = None,
        vector_db: Optional[VectorDB] = None,
        top_k: int = 4,
        score_threshold: float = 0.15,
    ):
        self.embedder = embedder or get_embedder()
        self.vector_db = vector_db or get_vector_db()
        self.top_k = top_k
        self.score_threshold = score_threshold

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Embed the query and retrieve top-k similar chunks."""
        k = top_k or self.top_k
        thresh = threshold if threshold is not None else self.score_threshold

        query_vec = self.embedder.embed_text(query)
        results = self.vector_db.query(
            query_embedding=query_vec,
            top_k=k,
            score_threshold=thresh,
        )
        if not results:
            results = self.vector_db.query(
                query_embedding=query_vec,
                top_k=k,
                score_threshold=0.0,
            )

        logger.info(f"Retrieved {len(results)} chunks for query: '{query[:50]}...'")
        return results


def get_retriever() -> RAGRetriever:
    """Factory to create configured retriever instance."""
    return RAGRetriever(
        top_k=settings.TOP_K,
        score_threshold=settings.SIMILARITY_THRESHOLD,
    )
