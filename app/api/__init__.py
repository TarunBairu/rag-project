from app.api.health import router as health_router
from app.api.documents import router as documents_router
from app.api.rag import router as rag_router

__all__ = ["health_router", "documents_router", "rag_router"]
