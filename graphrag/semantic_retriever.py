"""
graphrag/semantic_retriever.py
================================
FAISS-backed semantic retriever using sentence-transformers.
Drop-in replacement for GraphRetriever with the same public interface.

Requires:
    pip install faiss-cpu sentence-transformers

If the FAISS index does not exist, use get_retriever() from retriever.py
which falls back to TF-IDF GraphRetriever automatically.
"""

import json
import os
from typing import Optional

CHUNKS_PATH = os.path.join(os.path.dirname(__file__), "chunks.json")
FAISS_PATH  = os.path.join(os.path.dirname(__file__), "chunks.faiss")
IDMAP_PATH  = os.path.join(os.path.dirname(__file__), "id_map.json")
MODEL_NAME  = "all-MiniLM-L6-v2"


class SemanticRetriever:
    """
    Semantic retriever using sentence-transformers + FAISS.

    Public interface matches GraphRetriever:
        .retrieve(query, top_k, chunk_types)
        .retrieve_by_id(node_id)
        .get_context_text(query, top_k)
        .chunks  (list)
    """

    def __init__(
        self,
        chunks_path: str = CHUNKS_PATH,
        faiss_path: str = FAISS_PATH,
        idmap_path: str = IDMAP_PATH,
        model_name: str = MODEL_NAME,
    ):
        with open(chunks_path, encoding="utf-8") as f:
            self.chunks = json.load(f)

        with open(idmap_path, encoding="utf-8") as f:
            self._id_map = json.load(f)

        self._faiss_path = faiss_path
        self._model_name = model_name

        # Lazy-loaded
        self._index = None
        self._model = None

    def _load(self):
        """Load FAISS index and model on first use."""
        if self._index is not None:
            return
        try:
            import faiss
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise ImportError(
                f"Missing dependency: {e}\n"
                "Install with: pip install faiss-cpu sentence-transformers"
            )
        self._index = faiss.read_index(self._faiss_path)
        self._model = SentenceTransformer(self._model_name)

    def _embed(self, text: str):
        import numpy as np
        import faiss
        self._load()
        emb = self._model.encode([text], convert_to_numpy=True).astype("float32")
        faiss.normalize_L2(emb)
        return emb

    def retrieve(
        self,
        query: str,
        top_k: int = 15,
        chunk_types: Optional[list] = None,
    ) -> list:
        """Return top_k chunks most semantically similar to query."""
        if not query.strip():
            return []

        # Over-fetch to allow for chunk_types filtering
        fetch_k = top_k * 3 if chunk_types else top_k
        fetch_k = min(fetch_k, len(self.chunks))

        emb = self._embed(query)
        _, indices = self._index.search(emb, fetch_k)

        results = []
        for idx in indices[0]:
            if idx < 0 or idx >= len(self._id_map):
                continue
            chunk = self.chunks[self._id_map[idx]]
            if chunk_types and chunk.get("type") not in chunk_types:
                continue
            results.append(chunk)
            if len(results) >= top_k:
                break

        return results

    def retrieve_by_id(self, node_id: str) -> list:
        """Fetch all chunks for a specific node/edge ID (exact match)."""
        return [
            c for c in self.chunks
            if node_id in (c.get("node_id", ""), c.get("source", ""), c.get("target", ""))
        ]

    def get_context_text(self, query: str, top_k: int = 15) -> str:
        """Retrieve chunks and join their text for LLM context."""
        chunks = self.retrieve(query, top_k=top_k)
        if not chunks:
            return "No relevant graph context found."
        parts = [f"[{i}] ({c['type']}) {c['text']}" for i, c in enumerate(chunks, 1)]
        return "\n\n".join(parts)
