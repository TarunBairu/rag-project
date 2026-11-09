import logging
import traceback
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger("rag.middleware.error")


class RAGException(Exception):
    """Base exception for RAG project errors."""
    def __init__(self, message: str, status_code: int = 400, code: str = "BAD_REQUEST", detail: str = ""):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.detail = detail


class DocumentNotFoundError(RAGException):
    def __init__(self, document_id: str):
        super().__init__(
            message=f"Document with ID '{document_id}' not found.",
            status_code=404,
            code="DOCUMENT_NOT_FOUND",
        )


class IngestionError(RAGException):
    def __init__(self, message: str, detail: str = ""):
        super().__init__(
            message=message,
            status_code=422,
            code="INGESTION_ERROR",
            detail=detail,
        )


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Global catch-all exception middleware returning structured JSON responses."""

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except RAGException as rex:
            req_id = getattr(request.state, "request_id", "unknown")
            logger.warning(f"[{req_id}] Handled business error: {rex.message}")
            return JSONResponse(
                status_code=rex.status_code,
                content={
                    "success": False,
                    "error": {
                        "code": rex.code,
                        "message": rex.message,
                        "detail": rex.detail,
                    },
                    "request_id": req_id,
                },
                headers={"X-Request-ID": req_id},
            )
        except Exception as exc:
            req_id = getattr(request.state, "request_id", "unknown")
            stack_trace = traceback.format_exc()
            logger.error(f"[{req_id}] Unhandled server exception: {exc}\n{stack_trace}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected server error occurred.",
                        "detail": str(exc),
                    },
                    "request_id": req_id,
                },
                headers={"X-Request-ID": req_id},
            )
