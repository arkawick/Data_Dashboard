"""
tests/test_api.py
=================
Integration tests for the FastAPI GraphRAG endpoint.
Requires: graphrag/chunks.json to exist.

Run:
    # Start the API first:
    uvicorn graphrag.api:app --port 8001 &
    pytest tests/test_api.py -v

Or with pytest-asyncio + httpx:
    pytest tests/test_api.py -v
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

CHUNKS_PATH = os.path.join(os.path.dirname(__file__), "..", "graphrag", "chunks.json")


def _has_chunks():
    return os.path.exists(CHUNKS_PATH)


@pytest.mark.skipif(not _has_chunks(), reason="chunks.json not found")
class TestFastAPIEndpoints:

    @pytest.fixture(autouse=True)
    def client(self):
        from fastapi.testclient import TestClient
        from graphrag.api import app
        with TestClient(app) as c:
            self.client = c
            yield

    def test_health_ok(self):
        resp = self.client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["chunks_loaded"] >= 1000

    def test_health_has_retriever_type(self):
        resp = self.client.get("/health")
        assert "retriever_type" in resp.json()

    def test_graph_stats(self):
        resp = self.client.get("/graph/stats")
        assert resp.status_code == 200

    def test_chunk_search(self):
        resp = self.client.get("/chunks/search", params={"q": "critical bug", "top_k": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert "chunks" in data
        assert data["chunks_retrieved"] >= 0

    def test_chunk_search_empty_query_rejected(self):
        resp = self.client.get("/chunks/search", params={"q": ""})
        assert resp.status_code == 422   # Pydantic min_length validation

    def test_query_get_dry_run(self):
        resp = self.client.get("/query", params={"q": "critical bugs", "top_k": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert data["backend"] == "dry_run"
        assert data["question"] == "critical bugs"
        assert isinstance(data["chunks"], list)
        assert "DRY-RUN" in data["answer"]

    def test_query_post_dry_run(self):
        resp = self.client.post("/query", json={"question": "who leads the project", "top_k": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert data["backend"] == "dry_run"
        assert data["chunks_retrieved"] >= 0

    def test_query_post_with_chunk_types(self):
        resp = self.client.post("/query", json={
            "question": "employee roles",
            "top_k": 10,
            "chunk_types": ["entity"],
        })
        assert resp.status_code == 200

    def test_query_post_empty_question_rejected(self):
        resp = self.client.post("/query", json={"question": ""})
        assert resp.status_code == 422

    def test_metrics_endpoint_accessible(self):
        resp = self.client.get("/metrics")
        assert resp.status_code == 200
        assert b"graphrag_requests_total" in resp.content or b"python_info" in resp.content

    def test_pipeline_rebuild_without_redis(self):
        resp = self.client.post("/pipeline/rebuild")
        # Should return 503 if Celery/Redis is not running (acceptable in test env)
        assert resp.status_code in (200, 503)
