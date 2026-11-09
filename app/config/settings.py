import os
from functools import lru_cache
from pathlib import Path
from typing import List, Union

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    from pydantic import Field
    HAS_PYDANTIC_SETTINGS = True
except ImportError:  # Fallback for baseline environments
    from pydantic import BaseModel as BaseSettings, Field
    HAS_PYDANTIC_SETTINGS = False
    SettingsConfigDict = dict

# Project root directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Application runtime configuration."""
    
    # App Information
    APP_NAME: str = "RAG-Project"
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8001
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Base Paths
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = BASE_DIR / "data"
    LOGS_DIR: Path = BASE_DIR / "app" / "logs"

    # Database
    DATABASE_URL: str = "postgresql://rag_user:rag_password@localhost:5432/rag_db"
    SQLITE_FALLBACK_URL: str = f"sqlite:///{BASE_DIR / 'data' / 'rag.db'}"

    # Vector Store
    VECTOR_STORE_DIR: Path = BASE_DIR / "data" / "vector_store"
    VECTOR_COLLECTION_NAME: str = "rag_documents"

    # Embeddings
    EMBEDDING_PROVIDER: str = "mock"  # options: mock, sentence-transformers, openai, gemini
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # LLM Settings
    LLM_PROVIDER: str = "mock"  # options: mock, gemini, openai, groq
    LLM_MODEL: str = "llama3-8b-8192"
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 1024

    # Ingestion & Chunking
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50

    # Retriever
    TOP_K: int = 4
    SIMILARITY_THRESHOLD: float = 0.15

    # Middleware & Security
    RATE_LIMIT_REQUESTS: int = 60
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    CORS_ORIGINS: Union[List[str], str] = ["*"]

    if HAS_PYDANTIC_SETTINGS:
        model_config = SettingsConfigDict(
            env_file=str(BASE_DIR / ".env"),
            env_file_encoding="utf-8",
            extra="ignore",
        )

    def init_directories(self) -> None:
        """Ensure runtime directories exist."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self.VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    """Retrieve cached settings instance."""
    settings = Settings()
    settings.init_directories()
    return settings
