"""
tests/test_retriever.py
========================
Unit tests for GraphRetriever (TF-IDF).
Requires: graphrag/chunks.json to exist (checked in).
"""

import os
import sys
import pytest

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

CHUNKS_PATH = os.path.join(os.path.dirname(__file__), "..", "graphrag", "chunks.json")


def _has_chunks():
    return os.path.exists(CHUNKS_PATH)


@pytest.mark.skipif(not _has_chunks(), reason="chunks.json not found")
class TestGraphRetriever:

    def setup_method(self):
        from graphrag.retriever import GraphRetriever
        self.retriever = GraphRetriever(CHUNKS_PATH)

    def test_loads_chunks(self):
        assert len(self.retriever.chunks) >= 1000, (
            f"Expected >= 1000 chunks, got {len(self.retriever.chunks)}"
        )

    def test_retrieve_returns_results(self):
        results = self.retriever.retrieve("critical bug", top_k=5)
        assert len(results) > 0, "Expected results for 'critical bug'"

    def test_retrieve_empty_query(self):
        results = self.retriever.retrieve("", top_k=5)
        assert results == [], "Empty query should return empty list"

    def test_retrieve_whitespace_query(self):
        results = self.retriever.retrieve("   ", top_k=5)
        assert results == []

    def test_retrieve_top_k_respected(self):
        results = self.retriever.retrieve("employee project bug", top_k=3)
        assert len(results) <= 3

    def test_retrieve_chunk_types_filter(self):
        results = self.retriever.retrieve("employee", top_k=10, chunk_types=["entity"])
        for r in results:
            assert r["type"] == "entity", f"Unexpected type: {r['type']}"

    def test_retrieve_by_id(self):
        chunks = self.retriever.retrieve("employee", top_k=1)
        if chunks:
            node_id = chunks[0].get("node_id") or chunks[0].get("source")
            if node_id:
                found = self.retriever.retrieve_by_id(node_id)
                assert len(found) >= 1

    def test_get_context_text_returns_string(self):
        text = self.retriever.get_context_text("project bugs", top_k=5)
        assert isinstance(text, str)
        assert len(text) > 0

    def test_get_context_text_has_numbered_items(self):
        text = self.retriever.get_context_text("critical bugs", top_k=3)
        assert "[1]" in text

    def test_get_context_text_no_match(self):
        text = self.retriever.get_context_text("xyzzy12345nonexistent", top_k=5)
        assert "No relevant" in text


@pytest.mark.skipif(not _has_chunks(), reason="chunks.json not found")
def test_get_retriever_returns_graph_retriever_when_no_faiss():
    """get_retriever() should return GraphRetriever when no FAISS index exists."""
    import os as _os
    faiss_path = CHUNKS_PATH.replace("chunks.json", "chunks.faiss")

    if _os.path.exists(faiss_path):
        pytest.skip("FAISS index exists, skipping TF-IDF fallback test")

    from graphrag.retriever import get_retriever, GraphRetriever
    r = get_retriever(CHUNKS_PATH, prefer_semantic=True)
    assert isinstance(r, GraphRetriever)
