import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utc_now() -> datetime:
    """Return timezone-aware current UTC time."""
    return datetime.now(timezone.utc)


class Document(Base):
    """Metadata table for uploaded documents."""
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False, default="text/plain")
    chunk_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    """Chunk references linked to vector store IDs."""
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    vector_id = Column(String(64), nullable=False, index=True)
    chunk_metadata = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    document = relationship("Document", back_populates="chunks")


class QueryLog(Base):
    """Audit log of user queries and generated answers."""
    __tablename__ = "query_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    query_text = Column(Text, nullable=False)
    answer_text = Column(Text, nullable=False)
    retrieved_chunks = Column(Text, nullable=True)  # JSON-encoded chunk IDs / citations
    latency_ms = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), default=utc_now)
