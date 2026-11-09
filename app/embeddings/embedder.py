import hashlib
import logging
import math
from abc import ABC, abstractmethod
from typing import List
import numpy as np

from app.config.settings import get_settings

logger = logging.getLogger("rag.embeddings")
settings = get_settings()


class BaseEmbedder(ABC):
    """Abstract base class for text embedding generators."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the vector dimension."""
        pass

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding vector for a single string."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for a list of strings."""
        pass


class MockEmbedder(BaseEmbedder):
    """Fast, deterministic pseudo-embeddings for testing without heavy dependencies."""

    def __init__(self, dimension: int = 384):
        self._dim = dimension

    @property
    def dimension(self) -> int:
        return self._dim

    def _hash_to_vector(self, text: str) -> List[float]:
        clean = text.lower().strip()
        vec = np.zeros(self._dim, dtype=np.float32)
        words = clean.split()
        if not words:
            words = ["empty"]

        for i, word in enumerate(words):
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            for j in range(min(self._dim, 16)):
                idx = (h + j * 23) % self._dim
                val = ((h >> (j * 4)) & 0xFF) / 255.0 - 0.5
                vec[idx] += val * (1.0 / (math.log(i + 2)))

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def embed_text(self, text: str) -> List[float]:
        return self._hash_to_vector(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self._hash_to_vector(t) for t in texts]


class SentenceTransformerEmbedder(BaseEmbedder):
    """Local embedding generation using Hugging Face Sentence Transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            self._dim = self.model.get_sentence_embedding_dimension()
        except ImportError:
            raise ImportError(
                "sentence-transformers is not installed. Run `pip install sentence-transformers`"
            )

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_text(self, text: str) -> List[float]:
        vector = self.model.encode(text, normalize_embeddings=True)
        return vector.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        vectors = self.model.encode(texts, normalize_embeddings=True)
        return vectors.tolist()


class OpenAIEmbedder(BaseEmbedder):
    """OpenAI API Embeddings client."""

    def __init__(self, api_key: str = "", model: str = "text-embedding-3-small"):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model
        self._dim = 1536
        if not self.api_key:
            raise ValueError("OpenAI API key must be provided.")

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_text(self, text: str) -> List[float]:
        import httpx
        url = "https://api.openai.com/v1/embeddings"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        resp = httpx.post(url, headers=headers, json={"input": text, "model": self.model}, timeout=30.0)
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        import httpx
        url = "https://api.openai.com/v1/embeddings"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        resp = httpx.post(url, headers=headers, json={"input": texts, "model": self.model}, timeout=60.0)
        resp.raise_for_status()
        data = sorted(resp.json()["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in data]


def get_embedder() -> BaseEmbedder:
    """Factory to get configured embedding provider with automatic fallback."""
    provider = settings.EMBEDDING_PROVIDER.lower()
    
    if provider == "sentence-transformers":
        try:
            logger.info(f"Loading SentenceTransformer: {settings.EMBEDDING_MODEL}")
            return SentenceTransformerEmbedder(model_name=settings.EMBEDDING_MODEL)
        except Exception as exc:
            logger.warning(f"Failed to initialize SentenceTransformer ({exc}). Falling back to MockEmbedder.")
            return MockEmbedder(dimension=settings.EMBEDDING_DIMENSION)

    elif provider == "openai":
        try:
            return OpenAIEmbedder(api_key=settings.OPENAI_API_KEY)
        except Exception as exc:
            logger.warning(f"Failed to initialize OpenAIEmbedder ({exc}). Falling back to MockEmbedder.")
            return MockEmbedder(dimension=settings.EMBEDDING_DIMENSION)

    return MockEmbedder(dimension=settings.EMBEDDING_DIMENSION)
