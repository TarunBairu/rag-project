import json
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.db.models import Document, DocumentChunk
from app.db.postgres import get_db
from app.embeddings.embedder import get_embedder
from app.ingestion.chunker import TextChunker
from app.ingestion.loader import DocumentLoader
from app.middleware.error_handler import DocumentNotFoundError, IngestionError
from app.utils.helpers import compute_file_hash, format_bytes, sanitize_filename
from app.vectorstore.vector_db import get_vector_db

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])
settings = get_settings()


class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_size_formatted: str
    mime_type: str
    chunk_count: int
    created_at: str


class DocumentListResponse(BaseModel):
    total: int
    documents: List[DocumentResponse]


@router.post("/upload", status_code=status.HTTP_201_CREATED, summary="Upload & Ingest Document")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload a document (PDF, TXT, MD, CSV, DOCX), chunk it, generate embeddings,
    and persist vectors and relational metadata.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename must be provided.")

    clean_filename = sanitize_filename(file.filename)
    content_bytes = await file.read()

    if len(content_bytes) == 0:
        raise IngestionError(message="Uploaded file is empty.")

    # Calculate file hash for deduplication
    f_hash = compute_file_hash(content_bytes)
    existing = db.query(Document).filter(Document.file_hash == f_hash).first()
    if existing:
        return {
            "success": True,
            "message": "Document already ingested (duplicate content detected).",
            "document_id": existing.id,
            "filename": existing.filename,
            "chunk_count": existing.chunk_count,
        }

    # 1. Parse content
    try:
        parsed_doc = DocumentLoader.load_from_bytes(content_bytes, filename=clean_filename)
    except Exception as exc:
        raise IngestionError(message=f"Failed to parse document: {str(exc)}")

    raw_text = parsed_doc["text"]
    if not raw_text.strip():
        raise IngestionError(message="No extractable text found in file.")

    # 2. Chunk text
    chunker = TextChunker(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
    )
    doc_id = str(uuid.uuid4())
    chunks = chunker.chunk(
        text=raw_text,
        base_metadata={"document_id": doc_id, "filename": clean_filename},
    )

    if not chunks:
        raise IngestionError(message="Document produced 0 text chunks.")

    # 3. Generate embeddings
    embedder = get_embedder()
    chunk_texts = [c.content for c in chunks]
    embeddings = embedder.embed_batch(chunk_texts)

    # 4. Save to Vector DB
    vector_ids = [f"{doc_id}_{c.chunk_index}" for c in chunks]
    chunk_metas = [
        {
            "document_id": doc_id,
            "filename": clean_filename,
            "chunk_index": c.chunk_index,
            "token_count": c.token_count,
        }
        for c in chunks
    ]

    vdb = get_vector_db()
    vdb.add_documents(
        ids=vector_ids,
        embeddings=embeddings,
        documents=chunk_texts,
        metadatas=chunk_metas,
    )

    # 5. Save Relational Record to Database
    db_doc = Document(
        id=doc_id,
        filename=clean_filename,
        file_hash=f_hash,
        file_size=len(content_bytes),
        mime_type=file.content_type or "text/plain",
        chunk_count=len(chunks),
    )
    db.add(db_doc)

    for c, v_id in zip(chunks, vector_ids):
        db_chunk = DocumentChunk(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            chunk_index=c.chunk_index,
            content=c.content,
            vector_id=v_id,
            chunk_metadata=json.dumps(c.metadata),
        )
        db.add(db_chunk)

    db.commit()
    db.refresh(db_doc)

    return {
        "success": True,
        "message": f"Document '{clean_filename}' successfully processed and indexed.",
        "document_id": db_doc.id,
        "filename": db_doc.filename,
        "chunk_count": db_doc.chunk_count,
        "file_size": format_bytes(db_doc.file_size),
    }


@router.get("", response_model=DocumentListResponse, summary="List All Documents")
async def list_documents(db: Session = Depends(get_db)):
    """Retrieve metadata of all uploaded documents."""
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    results = [
        DocumentResponse(
            id=d.id,
            filename=d.filename,
            file_size_formatted=format_bytes(d.file_size),
            mime_type=d.mime_type,
            chunk_count=d.chunk_count,
            created_at=d.created_at.isoformat() if d.created_at else "",
        )
        for d in docs
    ]
    return DocumentListResponse(total=len(results), documents=results)


@router.delete("/{document_id}", summary="Delete Document and Chunks")
async def delete_document(document_id: str, db: Session = Depends(get_db)):
    """Delete a document, its database records, and its vector embeddings."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise DocumentNotFoundError(document_id=document_id)

    # Remove from Vector DB
    vdb = get_vector_db()
    deleted_vectors = vdb.delete_by_document_id(document_id)

    # Remove from Relational DB (cascade will remove chunks)
    db.delete(doc)
    db.commit()

    return {
        "success": True,
        "message": f"Document '{doc.filename}' and its {deleted_vectors} vector embeddings were deleted.",
        "document_id": document_id,
    }
