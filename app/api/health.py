from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.config.settings import get_settings
from app.db.postgres import get_db
from app.vectorstore.vector_db import get_vector_db

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get("/health", summary="Basic Liveness Probe")
async def liveness():
    """Returns basic liveness status."""
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV,
    }


@router.get("/health/ready", summary="Readiness Probe with DB & VectorStore Check")
async def readiness(db: Session = Depends(get_db)):
    """Verifies that database and vectorstore are reachable and operational."""
    db_status = "unhealthy"
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as exc:
        db_status = f"error: {str(exc)}"

    vector_status = "ready"
    vector_count = 0
    try:
        vdb = get_vector_db()
        vector_count = vdb.count()
    except Exception as exc:
        vector_status = f"error: {str(exc)}"

    is_ready = db_status == "connected" and not vector_status.startswith("error")

    return {
        "status": "healthy" if is_ready else "degraded",
        "database": db_status,
        "vector_store": vector_status,
        "total_vectors": vector_count,
    }
