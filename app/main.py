import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.documents import router as documents_router
from app.api.rag import router as rag_router
from app.config.settings import get_settings
from app.db.postgres import init_db
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.logger import RequestLoggerMiddleware, setup_logging
from app.middleware.rate_limiter import RateLimiterMiddleware

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management."""
    # Startup tasks
    setup_logging()
    logger = logging.getLogger("rag.app")
    logger.info(f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode...")
    settings.init_directories()
    init_db()
    logger.info("Application startup sequence completed.")

    yield

    # Shutdown tasks
    logger.info(f"Shutting down {settings.APP_NAME}...")


def create_app() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description="Production-grade Retrieval-Augmented Generation (RAG) API service.",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # 1. CORS Middleware
    origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Rate Limiting Middleware
    app.add_middleware(
        RateLimiterMiddleware,
        max_requests=settings.RATE_LIMIT_REQUESTS,
        window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
    )

    # 3. Global Exception Handler Middleware
    app.add_middleware(ErrorHandlerMiddleware)

    # 4. Request Logging & Metrics Middleware
    app.add_middleware(RequestLoggerMiddleware)

    # Register API Routers
    app.include_router(health_router)
    app.include_router(documents_router)
    app.include_router(rag_router)

    chat_html_path = settings.BASE_DIR / "app" / "templates" / "index.html"

    @app.get("/", response_class=HTMLResponse, tags=["UI"], summary="Web Chat UI")
    @app.get("/chat", response_class=HTMLResponse, tags=["UI"], summary="Web Chat UI")
    async def chat_ui():
        if chat_html_path.exists():
            with open(chat_html_path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        return HTMLResponse(content="<h1>RAG Chat UI</h1><p><a href='/docs'>Swagger API Docs</a></p>")

    @app.get("/api", tags=["Root"], summary="Root API Info")
    async def api_info():
        return {
            "name": settings.APP_NAME,
            "version": "1.0.0",
            "status": "online",
            "chat_ui": "/chat",
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health",
        }

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
    )
