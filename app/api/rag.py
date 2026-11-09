from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.postgres import get_db
from app.rag.pipeline import RAGPipeline, get_rag_pipeline

router = APIRouter(prefix="/api/v1/rag", tags=["RAG"])


class QueryRequest(BaseModel):
    query: str = Field(..., description="User question to be answered by RAG.", min_length=1)
    top_k: Optional[int] = Field(default=None, description="Number of context chunks to retrieve.")
    score_threshold: Optional[float] = Field(default=None, description="Minimum similarity score filter.")


class SourceItem(BaseModel):
    chunk_id: Optional[str]
    filename: str
    chunk_index: int
    score: float
    snippet: str


class QueryResponse(BaseModel):
    query: str
    answer: str
    sources: List[SourceItem]
    context_count: int
    latency_ms: float
    model: str


@router.post("/query", response_model=QueryResponse, summary="Query RAG System")
async def query_rag(
    payload: QueryRequest,
    db: Session = Depends(get_db),
    pipeline: RAGPipeline = Depends(get_rag_pipeline),
):
    """
    Query the knowledge base using semantic search and generate a grounded answer
    with source citations.
    """
    result = await pipeline.run(
        query=payload.query,
        top_k=payload.top_k,
        db=db,
    )
    return QueryResponse(**result)


@router.post("/query/stream", summary="Stream RAG Answer Generation")
async def stream_rag(
    payload: QueryRequest,
    pipeline: RAGPipeline = Depends(get_rag_pipeline),
):
    """
    Stream answer tokens using Server-Sent Events (SSE).
    """
    async def event_generator():
        async for token in pipeline.run_stream(query=payload.query, top_k=payload.top_k):
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
