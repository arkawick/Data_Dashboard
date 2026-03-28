"""
tests/test_graph.py
====================
Smoke tests for GraphRAG artifacts (graph.json, chunks.json).
These run fast and require no services -- just local files.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

GRAPHRAG_DIR = os.path.join(os.path.dirname(__file__), "..", "graphrag")
GRAPH_JSON   = os.path.join(GRAPHRAG_DIR, "graph.json")
CHUNKS_JSON  = os.path.join(GRAPHRAG_DIR, "chunks.json")


# ── graph.json ───────────────────────────────────────────────────────────────

@pytest.mark.skipif(not os.path.exists(GRAPH_JSON), reason="graph.json not found")
class TestGraphJson:

    @pytest.fixture(autouse=True)
    def load(self):
        with open(GRAPH_JSON, encoding="utf-8") as f:
            self.data = json.load(f)

    def test_has_nodes(self):
        assert "nodes" in self.data or "stats" in self.data

    def test_node_count_reasonable(self):
        stats = self.data.get("stats", {})
        nodes = stats.get("nodes", len(self.data.get("nodes", [])))
        assert nodes >= 100, f"Expected >= 100 nodes, got {nodes}"

    def test_edge_count_reasonable(self):
        stats = self.data.get("stats", {})
        edges = stats.get("edges", len(self.data.get("edges", [])))
        assert edges >= 200, f"Expected >= 200 edges, got {edges}"


# ── chunks.json ───────────────────────────────────────────────────────────────

@pytest.mark.skipif(not os.path.exists(CHUNKS_JSON), reason="chunks.json not found")
class TestChunksJson:

    @pytest.fixture(autouse=True)
    def load(self):
        with open(CHUNKS_JSON, encoding="utf-8") as f:
            self.chunks = json.load(f)

    def test_chunk_count(self):
        assert len(self.chunks) >= 1000, (
            f"Expected >= 1000 chunks, got {len(self.chunks)}"
        )

    def test_chunk_has_required_fields(self):
        required = {"id", "type", "text", "keywords"}
        for chunk in self.chunks[:10]:
            missing = required - set(chunk.keys())
            assert not missing, f"Chunk missing fields: {missing}"

    def test_chunk_types_valid(self):
        valid_types = {"entity", "relationship", "neighborhood"}
        for chunk in self.chunks:
            assert chunk["type"] in valid_types, f"Unknown type: {chunk['type']}"

    def test_chunks_are_ascii_safe(self):
        """Verify no Windows CP1252-breaking Unicode chars in chunk text."""
        problem_chars = ["\u2014", "\u2013", "\u2192", "\u2190", "\u2500"]
        for chunk in self.chunks:
            for char in problem_chars:
                assert char not in chunk["text"], (
                    f"Non-ASCII char '{char}' found in chunk {chunk['id']}"
                )

    def test_keyword_lists_non_empty(self):
        for chunk in self.chunks[:20]:
            assert len(chunk["keywords"]) > 0, (
                f"Chunk {chunk['id']} has empty keywords"
            )

    def test_entity_chunks_have_node_id(self):
        entity_chunks = [c for c in self.chunks if c["type"] == "entity"]
        assert len(entity_chunks) > 0
        for c in entity_chunks[:10]:
            assert "node_id" in c, f"Entity chunk missing node_id: {c['id']}"

    def test_relationship_chunks_have_source_target(self):
        rel_chunks = [c for c in self.chunks if c["type"] == "relationship"]
        assert len(rel_chunks) > 0
        for c in rel_chunks[:10]:
            assert "source" in c and "target" in c, (
                f"Relationship chunk missing source/target: {c['id']}"
            )
