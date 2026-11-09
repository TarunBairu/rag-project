import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_and_chat_endpoints():
    # Chat UI endpoint
    response = client.get("/")
    assert response.status_code == 200
    assert "RAG Workspace" in response.text

    chat_res = client.get("/chat")
    assert chat_res.status_code == 200
    assert "RAG Workspace" in chat_res.text

    # JSON metadata endpoint
    api_res = client.get("/api")
    assert api_res.status_code == 200
    data = api_res.json()
    assert data["status"] == "online"
    assert "chat_ui" in data


def test_health_endpoints():
    res_liveness = client.get("/health")
    assert res_liveness.status_code == 200
    assert res_liveness.json()["status"] == "ok"

    res_readiness = client.get("/health/ready")
    assert res_readiness.status_code == 200
    assert "database" in res_readiness.json()
    assert "vector_store" in res_readiness.json()


def test_document_lifecycle_and_rag_query():
    # 1. Upload a document
    file_content = (
        b"Retrieval-Augmented Generation (RAG) optimizes the output of large language models "
        b"with targeted information retrieved from external knowledge bases."
    )
    files = {"file": ("rag_overview.txt", file_content, "text/plain")}

    upload_res = client.post("/api/v1/documents/upload", files=files)
    assert upload_res.status_code == 201
    upload_data = upload_res.json()
    assert upload_data["success"] is True
    doc_id = upload_data["document_id"]
    assert upload_data["chunk_count"] >= 1

    # 2. List documents
    list_res = client.get("/api/v1/documents")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    found = any(d["id"] == doc_id for d in list_data["documents"])
    assert found is True

    # 3. Query RAG
    query_payload = {
        "query": "What does Retrieval-Augmented Generation optimize?",
        "top_k": 2,
    }
    query_res = client.post("/api/v1/rag/query", json=query_payload)
    assert query_res.status_code == 200
    query_data = query_res.json()
    assert "answer" in query_data
    assert len(query_data["sources"]) >= 1
    assert query_data["sources"][0]["filename"] == "rag_overview.txt"

    # 4. Delete document
    del_res = client.delete(f"/api/v1/documents/{doc_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # 5. Delete non-existent document should return 404
    del_nonexistent = client.delete(f"/api/v1/documents/non_existent_id_123")
    assert del_nonexistent.status_code == 404
