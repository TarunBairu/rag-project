import json
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.db.models import QueryLog
from app.rag.generator import BaseGenerator, get_generator
from app.rag.prompt_builder import PromptBuilder
from app.rag.retriever import RAGRetriever, get_retriever

logger = logging.getLogger("rag.pipeline")
settings = get_settings()


class RAGPipeline:
    """End-to-end RAG orchestrator for document retrieval, prompt assembly, and answer generation."""

    def __init__(
        self,
        retriever: Optional[RAGRetriever] = None,
        generator: Optional[BaseGenerator] = None,
    ):
        self.retriever = retriever or get_retriever()
        self.generator = generator or get_generator()

    async def run(
        self,
        query: str,
        top_k: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """Execute non-streaming RAG query pipeline."""
        start_time = time.perf_counter()

        # Step 1: Retrieval
        chunks = self.retriever.retrieve(query=query, top_k=top_k)

        # Step 2: Prompt Building
        prompt_payload = PromptBuilder.build_prompt(query=query, retrieved_chunks=chunks)

        # Step 3: Generation
        answer = await self.generator.generate(prompt_payload)

        # Latency calculation
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        # Step 4: Audit Logging in DB
        sources = []
        for c in chunks:
            meta = c.get("metadata") or {}
            sources.append({
                "chunk_id": c.get("id"),
                "filename": meta.get("filename", "Unknown"),
                "chunk_index": meta.get("chunk_index", 0),
                "score": round(c.get("score", 0.0), 4),
                "snippet": (c.get("document", "")[:150] + "...") if len(c.get("document", "")) > 150 else c.get("document", ""),
            })

        if db is not None:
            try:
                log_entry = QueryLog(
                    query_text=query,
                    answer_text=answer,
                    retrieved_chunks=json.dumps([s["chunk_id"] for s in sources]),
                    latency_ms=round(latency_ms, 2),
                )
                db.add(log_entry)
                db.commit()
            except Exception as exc:
                logger.error(f"Failed to save query log: {exc}")
                db.rollback()

        return {
            "query": query,
            "answer": answer,
            "sources": sources,
            "context_count": len(chunks),
            "latency_ms": round(latency_ms, 2),
            "model": getattr(self.generator, "model", "mock-synthesizer") if getattr(self.generator, "model", None) else ("mock-synthesizer" if settings.LLM_PROVIDER == "mock" else settings.LLM_MODEL),
        }

    async def run_stream(
        self,
        query: str,
        top_k: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """Execute streaming RAG query yielding token deltas."""
        chunks = self.retriever.retrieve(query=query, top_k=top_k)
        prompt_payload = PromptBuilder.build_prompt(query=query, retrieved_chunks=chunks)

        async for token in self.generator.generate_stream(prompt_payload):
            yield token


def get_rag_pipeline() -> RAGPipeline:
    """Factory to retrieve singleton RAG pipeline."""
    return RAGPipeline()
