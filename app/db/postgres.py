import logging
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import OperationalError

from app.config.settings import get_settings
from app.db.models import Base

logger = logging.getLogger("rag.db")
settings = get_settings()


def create_db_engine():
    """Create database engine with automatic fallback to SQLite if PostgreSQL is unreachable."""
    postgres_url = settings.DATABASE_URL
    sqlite_url = settings.SQLITE_FALLBACK_URL

    # Attempt PostgreSQL connection
    try:
        engine = create_engine(
            postgres_url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 3} if "postgresql" in postgres_url else {}
        )
        with engine.connect():
            pass
        logger.info("Successfully connected to primary PostgreSQL database.")
        return engine
    except Exception as exc:
        logger.warning(
            f"Could not connect to PostgreSQL ({exc}). Falling back to local SQLite database at {sqlite_url}"
        )
        # SQLite engine fallback
        fallback_engine = create_engine(
            sqlite_url,
            connect_args={"check_same_thread": False}
        )
        return fallback_engine


engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Initialize database tables."""
    try:
        settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully.")
    except Exception as exc:
        logger.error(f"Error creating database tables: {exc}")
        raise


# Auto-initialize tables on import
try:
    init_db()
except Exception:
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

