"""
graphrag/hybrid_retriever.py
============================
Hybrid retriever: FAISS semantic search + Neo4j 2-hop graph expansion.

Combines:
  1. SemanticRetriever  -- finds top-K chunks by meaning
  2. Neo4jRetriever     -- expands to 2-hop neighbours of matched nodes in Neo4j

Falls back gracefully if Neo4j is unavailable.

Usage:
    hr = HybridRetriever()
    result = hr.retrieve("critical bugs in Finance", top_k=15)
    # result["chunks"]          -- list of chunk dicts
    # result["graph_paths"]     -- list of {source, relation, target} dicts
    # result["combined_context"]-- merged text for LLM prompt
"""

import os


class HybridRetriever:

    def __init__(
        self,
        chunks_path: str = None,
        faiss_path: str = None,
        neo4j_uri: str = None,
        neo4j_user: str = None,
        neo4j_password: str = None,
    ):
        from graphrag.retriever import get_retriever, CHUNKS_PATH
        import os as _os

        _chunks_path = chunks_path or CHUNKS_PATH
        _faiss_path  = faiss_path or _chunks_path.replace("chunks.json", "chunks.faiss")

        self._retriever  = get_retriever(_chunks_path)
        self._neo4j_uri  = neo4j_uri  or _os.environ.get("NEO4J_URI",      "bolt://localhost:7687")
        self._neo4j_user = neo4j_user or _os.environ.get("NEO4J_USER",     "neo4j")
        self._neo4j_pwd  = neo4j_password or _os.environ.get("NEO4J_PASSWORD", "password")

    def retrieve(self, query: str, top_k: int = 15) -> dict:
        """
        Returns:
            {
              "chunks":           list of chunk dicts from FAISS/TF-IDF,
              "graph_paths":      list of {source, relation, target} from Neo4j,
              "combined_context": merged text for LLM prompt,
            }
        """
        # Step 1: semantic / TF-IDF chunk retrieval
        chunks = self._retriever.retrieve(query, top_k=top_k)

        # Step 2: collect node IDs from retrieved chunks
        node_ids = set()
        for c in chunks:
            for key in ("node_id", "source", "target"):
                val = c.get(key)
                if val:
                    node_ids.add(val)

        # Step 3: Neo4j graph expansion
        graph_paths = []
        neo4j_text = ""
        if node_ids:
            try:
                from graphrag.neo4j_retriever import Neo4jRetriever
                with Neo4jRetriever(self._neo4j_uri, self._neo4j_user, self._neo4j_pwd) as nr:
                    graph_paths = nr.get_node_context(list(node_ids), hops=2)
                    neo4j_text = nr.format_for_llm(graph_paths)
            except Exception as exc:
                print(f"[HybridRetriever] Neo4j unavailable, using chunks only. ({exc})")

        # Step 4: merge context
        chunk_text = "\n\n".join(
            f"[{i}] ({c['type']}) {c['text']}" for i, c in enumerate(chunks, 1)
        )
        combined = chunk_text
        if neo4j_text:
            combined = chunk_text + "\n\n" + neo4j_text

        return {
            "chunks":            chunks,
            "graph_paths":       graph_paths,
            "combined_context":  combined,
        }
