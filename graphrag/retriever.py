"""
graphrag/retriever.py
=====================
TF-IDF retriever over graph chunks.
Used by query.py to find chunks most relevant to a user question.

Can also be run standalone for interactive testing:
    python graphrag/retriever.py
"""

import json
import math
import os
import re
from collections import Counter

CHUNKS_PATH = os.path.join(os.path.dirname(__file__), "chunks.json")


def tokenize(text):
    return re.findall(r"[a-z0-9\-]+", text.lower())


class GraphRetriever:
    def __init__(self, chunks_path=CHUNKS_PATH):
        with open(chunks_path, encoding="utf-8") as f:
            self.chunks = json.load(f)

        # Build IDF from chunk keywords
        N = len(self.chunks)
        df = Counter()
        for chunk in self.chunks:
            for kw in set(chunk["keywords"]):
                df[kw] += 1
        self.idf = {term: math.log((N + 1) / (freq + 1)) + 1 for term, freq in df.items()}

    def _score(self, query_terms, chunk):
        kw_set    = set(chunk["keywords"])
        kw_counter = Counter(chunk["keywords"])
        total_kw  = len(chunk["keywords"]) or 1

        score = 0.0
        for term in query_terms:
            if term in kw_set:
                tf  = kw_counter[term] / total_kw
                idf = self.idf.get(term, 1.0)
                score += tf * idf
        return score

    def retrieve(self, query, top_k=15, chunk_types=None):
        """
        Return the top_k most relevant chunks for a query string.

        chunk_types: list of types to include, e.g. ["entity", "relationship"]
                     None = all types
        """
        query_terms = tokenize(query)
        if not query_terms:
            return []

        scored = []
        for chunk in self.chunks:
            if chunk_types and chunk["type"] not in chunk_types:
                continue
            s = self._score(query_terms, chunk)
            if s > 0:
                scored.append((s, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:top_k]]

    def retrieve_by_id(self, node_id):
        """Fetch all chunks associated with a specific node/edge ID."""
        return [
            c for c in self.chunks
            if node_id in (c.get("node_id", ""), c.get("source", ""), c.get("target", ""))
        ]

    def get_context_text(self, query, top_k=15):
        """Convenience: retrieve chunks and join their text for LLM context."""
        chunks = self.retrieve(query, top_k=top_k)
        if not chunks:
            return "No relevant graph context found."
        parts = []
        for i, c in enumerate(chunks, 1):
            parts.append(f"[{i}] ({c['type']}) {c['text']}")
        return "\n\n".join(parts)


def get_retriever(chunks_path=CHUNKS_PATH, prefer_semantic=True):
    """
    Factory: returns SemanticRetriever (FAISS) if index exists, else GraphRetriever (TF-IDF).

    Usage:
        from graphrag.retriever import get_retriever
        r = get_retriever()          # auto-selects best available
        chunks = r.retrieve("critical bugs", top_k=10)
    """
    if prefer_semantic:
        faiss_path = chunks_path.replace("chunks.json", "chunks.faiss")
        idmap_path = chunks_path.replace("chunks.json", "id_map.json")
        if os.path.exists(faiss_path) and os.path.exists(idmap_path):
            try:
                from graphrag.semantic_retriever import SemanticRetriever
                return SemanticRetriever(chunks_path, faiss_path, idmap_path)
            except ImportError:
                pass  # sentence-transformers/faiss not installed, fall through
    return GraphRetriever(chunks_path)


if __name__ == "__main__":
    retriever = GraphRetriever()
    print(f"Loaded {len(retriever.chunks)} chunks.\n")
    while True:
        q = input("Search query (or 'q' to quit): ").strip()
        if q.lower() == "q":
            break
        results = retriever.retrieve(q, top_k=5)
        print(f"\n  Top {len(results)} results:")
        for c in results:
            print(f"  [{c['type']:12}] {c['id']}")
            print(f"    {c['text'][:120]}...")
        print()
