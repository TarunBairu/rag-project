# RAG - PROJECT

A modular, production-ready **Retrieval-Augmented Generation (RAG)** service built with FastAPI, PostgreSQL, vector embeddings, document chunking, prompt synthesis, and real-time streaming.

---

## Architecture & Directory Layout

Directly based on the architectural blueprint:

```
rag-project/
├── app/
│   ├── main.py                  # FastAPI Entry Point
│   ├── api/
│   │   ├── rag.py               # RAG APIs (Query & Streaming)
│   │   ├── documents.py         # Upload/Delete Docs & Document Management
│   │   └── health.py            # Health & Readiness Probes
│   ├── middleware/
│   │   ├── error_handler.py     # Global Exception & Error Handler
│   │   ├── logger.py            # Request/Response Logging with X-Request-ID
│   │   └── rate_limiter.py      # IP-based Sliding Window Rate Limiting
│   ├── rag/
│   │   ├── pipeline.py          # Main RAG Orchestration Flow
│   │   ├── retriever.py         # Semantic Search & Score Filtering
│   │   ├── generator.py         # LLM Generation (Gemini, OpenAI, Mock)
│   │   └── prompt_builder.py    # Structured Grounded Prompt Assembly
│   ├── ingestion/
│   │   ├── loader.py            # Multi-format File Loader (PDF, TXT, MD, CSV, DOCX)
│   │   ├── chunker.py           # Recursive Character Chunker with Overlap
│   │   └── parser.py            # Document Parsing & Metadata Extraction
│   ├── embeddings/
│   │   └── embedder.py          # Text Embeddings (SentenceTransformers, OpenAI, Mock)
│   ├── vectorstore/
│   │   └── vector_db.py         # Vector Database Operations (ChromaDB & Numpy Store)
│   ├── db/
│   │   ├── postgres.py          # PostgreSQL Connection & Auto-SQLite Fallback
│   │   └── models.py            # SQLAlchemy Relational Models
│   ├── logs/
│   │   ├── app.log              # Application Request Logs
│   │   └── error.log            # Unhandled & Error Trace Logs
│   ├── config/
│   │   └── settings.py          # Pydantic Settings & Environment Loading
│   └── utils/
│       └── helpers.py           # Hashing, Token Estimation & String Utilities
├── tests/
│   ├── test_rag.py              # Unit Tests for RAG Ingestion, Chunker & Pipeline
│   └── test_api.py              # Integration Tests for API Endpoints
├── docker/
│   ├── Dockerfile               # Production Multi-stage Container Image
│   └── docker-compose.yml       # Multi-container Setup (App + PostgreSQL with pgvector)
├── github/
│   └── workflows/
│       └── ci.yml               # GitHub Actions CI Workflow
├── .github/
│   └── workflows/
│       └── ci.yml               # Standard GitHub Actions Workflow Mirror
├── .env                         # Environment Variables Configuration
├── requirements.txt             # Python Dependencies
├── README.md                    # Project Documentation
└── Makefile                     # Developer Commands
```

---

## Key Features

1. **Multi-Format Ingestion**: Supports `.pdf`, `.txt`, `.md`, `.csv`, `.docx`, and `.json`.
2. **Deterministic & Semantic Chunking**: Recursive character chunker with configurable chunk size and overlap, propagating positional metadata.
3. **Pluggable Vector Store**: Uses ChromaDB with persistent storage, backed by a persistent high-performance vector search engine.
4. **Resilient Database Layer**: Primary PostgreSQL support with automatic SQLite fallback (`./data/rag.db`) so the project runs immediately with zero external dependencies.
5. **Multi-Model Answer Generator**: Connects to **Google Gemini** or **OpenAI**, with a built-in offline synthesizer for testing.
6. **Robust Middleware Stack**:
   - Request logger with unique `X-Request-ID` and latency tracking.
   - Global exception handling returning clean JSON envelopes.
   - Sliding-window rate limiter per client IP.
7. **Production Ready**: Includes multi-stage Docker build, Docker Compose, automated Pytest suite, and GitHub Actions CI.

---

## Quickstart Guide

### 1. Prerequisites
- Python 3.10+
- (Optional) Docker and Docker Compose

### 2. Installation
```bash
# Clone or navigate to the directory
cd rag-project

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment
A default `.env` file is included. Edit `.env` to configure your API keys if using cloud LLMs:
```env
# Optional cloud providers:
LLM_PROVIDER=groq         # 'groq', 'gemini', 'openai', or 'mock'
GROQ_API_KEY=gsk_your_groq_api_key_here
LLM_MODEL=llama-3.3-70b-versatile  # or 'llama-3.1-8b-instant'

# or Google Gemini:
# LLM_PROVIDER=gemini
# GEMINI_API_KEY=your_key_here

# or OpenAI:
# LLM_PROVIDER=openai
# OPENAI_API_KEY=your_key_here
```

### 4. Run the Application
```bash
# Using Makefile
make run

# Or directly with uvicorn
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

The interactive Web Chat UI is available at:
👉 **http://localhost:8001/chat** (or simply **http://localhost:8001/**)

The interactive Swagger documentation is available at:
👉 **http://localhost:8001/docs**

---

## API Usage Examples

### 1. Health Checks
```bash
# Liveness probe
curl -X GET http://localhost:8001/health

# Readiness check (DB + Vector DB)
curl -X GET http://localhost:8001/health/ready
```

### 2. Upload a Document
```bash
curl -X POST http://localhost:8001/api/v1/documents/upload \
  -F "file=@sample.txt"
```
**Response:**
```json
{
  "success": true,
  "message": "Document 'sample.txt' successfully processed and indexed.",
  "document_id": "5174092b-81d3-49d7-84bc-875f5fe22144",
  "filename": "sample.txt",
  "chunk_count": 4,
  "file_size": "1.42 KB"
}
```

### 3. List Documents
```bash
curl -X GET http://localhost:8001/api/v1/documents
```

### 4. Query RAG
```bash
curl -X POST http://localhost:8001/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the primary findings in the uploaded document?",
    "top_k": 3
  }'
```
**Response:**
```json
{
  "query": "What are the primary findings in the uploaded document?",
  "answer": "Based on the retrieved documents, ... [Source 1]",
  "sources": [
    {
      "chunk_id": "5174092b-81d3-49d7-84bc-875f5fe22144_0",
      "filename": "sample.txt",
      "chunk_index": 0,
      "score": 0.892,
      "snippet": "Excerpts from the text..."
    }
  ],
  "context_count": 1,
  "latency_ms": 42.15,
  "model": "gemini-1.5-flash"
}
```

### 5. Stream Answer Tokens (Server-Sent Events)
```bash
curl -N -X POST http://localhost:8001/api/v1/rag/query/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "Summarize the project architecture"}'
```

### 6. Delete Document
```bash
curl -X DELETE http://localhost:8001/api/v1/documents/{document_id}
```

---

## Running Automated Tests

Run the test suite using `pytest`:
```bash
make test
# or
pytest tests/ -v
```

---

## Docker & Multi-Container Setup

To launch the full stack including PostgreSQL with `pgvector`:
```bash
# Start containers in background
make docker-up
# or
docker compose -f docker/docker-compose.yml up --build -d

# View logs
docker compose -f docker/docker-compose.yml logs -f

# Tear down
make docker-down
```
