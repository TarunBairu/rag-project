import pytest
from app.embeddings.embedder import MockEmbedder
from app.ingestion.chunker import TextChunker
from app.ingestion.loader import DocumentLoader
from app.ingestion.parser import DocumentParser
from app.rag.generator import MockGenerator
from app.rag.pipeline import RAGPipeline
from app.rag.prompt_builder import PromptBuilder
from app.rag.retriever import RAGRetriever
from app.vectorstore.vector_db import VectorDB


def test_document_parser():
    raw_text = "   # Title Of Document  \n\nThis is a sample paragraph with extra   spaces.\n\nNext line."
    parsed = DocumentParser.parse(raw_text, filename="doc.txt")
    assert parsed["metadata"]["title"] == "Title Of Document"
    assert parsed["metadata"]["word_count"] > 5
    assert "extra spaces." in parsed["cleaned_text"]


def test_text_chunker():
    chunker = TextChunker(chunk_size=50, chunk_overlap=10)
    text = "Machine learning is a branch of artificial intelligence. It focuses on the use of data and algorithms to imitate the way that humans learn."
    chunks = chunker.chunk(text, base_metadata={"doc": "test"})
    assert len(chunks) > 1
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1
    assert chunks[0].metadata["doc"] == "test"


def test_document_loader_txt_and_csv():
    txt_content = b"Simple document line 1\nLine 2"
    loaded_txt = DocumentLoader.load_from_bytes(txt_content, "sample.txt")
    assert loaded_txt["file_type"] == "txt"
    assert "Simple document" in loaded_txt["text"]

    csv_content = b"col1,col2\nval1,val2\nval3,val4"
    loaded_csv = DocumentLoader.load_from_bytes(csv_content, "data.csv")
    assert loaded_csv["file_type"] == "csv"
    assert "col1 | col2" in loaded_csv["text"]


def test_mock_embedder():
    embedder = MockEmbedder(dimension=128)
    vec1 = embedder.embed_text("FastAPI RAG Pipeline")
    vec2 = embedder.embed_text("FastAPI RAG Pipeline")
    vec3 = embedder.embed_text("Something completely different")

    assert len(vec1) == 128
    assert vec1 == vec2  # Deterministic
    assert vec1 != vec3


def test_vector_db_operations(tmp_path):
    vdb = VectorDB(storage_dir=tmp_path, collection_name="test_col")
    embedder = MockEmbedder(dimension=64)

    doc_texts = ["PostgreSQL database storage", "ChromaDB vector search", "FastAPI web framework"]
    vectors = embedder.embed_batch(doc_texts)
    ids = ["doc_1", "doc_2", "doc_3"]
    metas = [{"document_id": "d1"}, {"document_id": "d2"}, {"document_id": "d3"}]

    vdb.add_documents(ids=ids, embeddings=vectors, documents=doc_texts, metadatas=metas)
    assert vdb.count() >= 3

    # Query
    q_vec = embedder.embed_text("vector search")
    results = vdb.query(q_vec, top_k=2)
    assert len(results) > 0
    assert "document" in results[0]

    # Delete
    deleted = vdb.delete_by_document_id("d2")
    assert deleted >= 1


def test_prompt_builder():
    chunks = [
        {
            "id": "c1",
            "document": "RAG stands for Retrieval-Augmented Generation.",
            "metadata": {"filename": "rag_intro.txt", "chunk_index": 0},
            "score": 0.95,
        }
    ]
    prompt = PromptBuilder.build_prompt("What is RAG?", chunks)
    assert "RAG stands for" in prompt["user_prompt"]
    assert "[Source 1" in prompt["user_prompt"]
    assert "What is RAG?" in prompt["user_prompt"]


@pytest.mark.asyncio
async def test_rag_pipeline(tmp_path):
    embedder = MockEmbedder(dimension=64)
    vdb = VectorDB(storage_dir=tmp_path, collection_name="test_pipe")
    
    # Ingest mock doc
    text = "Python 3.11 introduces faster execution speed and exception groups."
    vec = embedder.embed_text(text)
    vdb.add_documents(
        ids=["py_chunk_0"],
        embeddings=[vec],
        documents=[text],
        metadatas=[{"document_id": "py_doc", "filename": "python.txt", "chunk_index": 0}]
    )

    retriever = RAGRetriever(embedder=embedder, vector_db=vdb, top_k=2, score_threshold=0.0)
    generator = MockGenerator()
    pipeline = RAGPipeline(retriever=retriever, generator=generator)

    result = await pipeline.run(query="What does Python 3.11 introduce?")
    assert "answer" in result
    assert "sources" in result
    assert len(result["sources"]) > 0
    assert result["sources"][0]["filename"] == "python.txt"
