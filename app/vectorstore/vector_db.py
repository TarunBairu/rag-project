import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np

from app.config.settings import get_settings

logger = logging.getLogger("rag.vectorstore")
settings = get_settings()


class VectorDB:
    """Vector database manager supporting ChromaDB with native Numpy fallback."""

    def __init__(self, storage_dir: Optional[Path] = None, collection_name: str = "rag_documents"):
        self.storage_dir = storage_dir or settings.VECTOR_STORE_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self.chroma_client = None
        self.collection = None
        self._init_backend()

    def _init_backend(self) -> None:
        """Initialize ChromaDB or fallback to persistent numpy store."""
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            self.chroma_client = chromadb.PersistentClient(
                path=str(self.storage_dir),
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            self.collection = self.chroma_client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Initialized ChromaDB persistent backend at {self.storage_dir}")
        except Exception as exc:
            logger.warning(
                f"ChromaDB unavailable ({exc}). Using high-performance persistent Numpy Vector Store."
            )
            self.chroma_client = None
            self._data_file = self.storage_dir / f"{self.collection_name}.json"
            self._cache: Dict[str, Dict[str, Any]] = self._load_local_store()

    def _load_local_store(self) -> Dict[str, Dict[str, Any]]:
        if self._data_file.exists():
            try:
                with open(self._data_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as exc:
                logger.error(f"Error loading local vector file: {exc}")
        return {}

    def _save_local_store(self) -> None:
        try:
            with open(self._data_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f)
        except Exception as exc:
            logger.error(f"Error saving local vector store: {exc}")

    def add_documents(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Add document embeddings and payloads into the vector store."""
        if not ids:
            return

        if metadatas is None:
            metadatas = [{} for _ in ids]

        if self.collection is not None:
            # ChromaDB expects string/number/bool in metadata
            cleaned_metadatas = []
            for meta in metadatas:
                cleaned = {k: (str(v) if not isinstance(v, (str, int, float, bool)) else v) for k, v in meta.items()}
                cleaned_metadatas.append(cleaned)
            self.collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=cleaned_metadatas
            )
        else:
            for i, chunk_id in enumerate(ids):
                self._cache[chunk_id] = {
                    "id": chunk_id,
                    "embedding": embeddings[i],
                    "document": documents[i],
                    "metadata": metadatas[i],
                }
            self._save_local_store()

    def query(
        self,
        query_embedding: List[float],
        top_k: int = 4,
        score_threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Query similar items by cosine similarity."""
        if self.collection is not None:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            matched = []
            if results and results.get("ids") and results["ids"][0]:
                for i, chunk_id in enumerate(results["ids"][0]):
                    dist = results["distances"][0][i] if results.get("distances") else 0.0
                    # For cosine distance: similarity = 1 - distance
                    similarity = 1.0 - dist
                    if similarity >= score_threshold:
                        matched.append({
                            "id": chunk_id,
                            "document": results["documents"][0][i],
                            "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                            "score": float(similarity),
                        })
            return matched
        else:
            if not self._cache:
                return []

            q_vec = np.array(query_embedding, dtype=np.float32)
            q_norm = np.linalg.norm(q_vec)
            if q_norm == 0:
                q_norm = 1.0

            scored = []
            for item in self._cache.values():
                d_vec = np.array(item["embedding"], dtype=np.float32)
                d_norm = np.linalg.norm(d_vec)
                if d_norm == 0:
                    d_norm = 1.0
                similarity = float(np.dot(q_vec, d_vec) / (q_norm * d_norm))
                if similarity >= score_threshold:
                    scored.append({
                        "id": item["id"],
                        "document": item["document"],
                        "metadata": item["metadata"],
                        "score": similarity,
                    })

            scored.sort(key=lambda x: x["score"], reverse=True)
            return scored[:top_k]

    def delete_by_document_id(self, document_id: str) -> int:
        """Delete all chunks associated with a specific document ID."""
        deleted_count = 0
        if self.collection is not None:
            # Query IDs with matching document_id metadata
            matching = self.collection.get(where={"document_id": document_id})
            if matching and matching.get("ids"):
                deleted_count = len(matching["ids"])
                self.collection.delete(ids=matching["ids"])
        else:
            keys_to_del = [
                k for k, v in self._cache.items()
                if v.get("metadata", {}).get("document_id") == document_id
            ]
            deleted_count = len(keys_to_del)
            for k in keys_to_del:
                del self._cache[k]
            if deleted_count > 0:
                self._save_local_store()

        return deleted_count

    def count(self) -> int:
        """Return total number of vectors in the store."""
        if self.collection is not None:
            return self.collection.count()
        return len(self._cache)


_vector_db_instance: Optional[VectorDB] = None


def get_vector_db() -> VectorDB:
    """Singleton getter for VectorDB."""
    global _vector_db_instance
    if _vector_db_instance is None:
        _vector_db_instance = VectorDB()
    return _vector_db_instance
