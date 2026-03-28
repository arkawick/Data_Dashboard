"""
graphrag/neo4j_retriever.py
============================
Neo4j context retriever for multi-hop graph expansion.
Used by HybridRetriever to complement FAISS chunk results
with 2-hop graph paths from Neo4j.

Requires:
    pip install neo4j
    Neo4j running at bolt://localhost:7687

Usage:
    with Neo4jRetriever(uri, user, password) as r:
        paths = r.get_node_context(["EMP-001", "PROJ-003"])
        text  = r.format_for_llm(paths)
"""

import os


class Neo4jRetriever:
    """
    Fetches multi-hop graph context from Neo4j for a list of node IDs.

    The _node_id property in Neo4j was set by load_neo4j.py.
    """

    def __init__(self, uri: str = None, user: str = None, password: str = None):
        self._uri  = uri      or os.environ.get("NEO4J_URI",      "bolt://localhost:7687")
        self._user = user     or os.environ.get("NEO4J_USER",     "neo4j")
        self._pwd  = password or os.environ.get("NEO4J_PASSWORD", "password")
        self._driver = None

    def _connect(self):
        from neo4j import GraphDatabase
        self._driver = GraphDatabase.driver(self._uri, auth=(self._user, self._pwd))

    def __enter__(self):
        self._connect()
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None

    def ping(self) -> bool:
        """Return True if Neo4j is reachable."""
        try:
            if not self._driver:
                self._connect()
            self._driver.verify_connectivity()
            return True
        except Exception:
            return False

    def get_node_context(self, node_ids: list, hops: int = 2) -> list:
        """
        Fetch up to 2-hop neighbours for a list of node IDs.
        Returns list of path dicts: {source, relation, target, src_label, tgt_label}.
        """
        if not node_ids:
            return []
        if not self._driver:
            self._connect()

        cypher = (
            "MATCH (start)-[r*1..{hops}]-(neighbor) "
            "WHERE start._node_id IN $node_ids "
            "UNWIND r AS rel "
            "RETURN startNode(rel)._node_id AS source, "
            "       type(rel) AS relation, "
            "       endNode(rel)._node_id AS target, "
            "       labels(startNode(rel))[0] AS src_label, "
            "       labels(endNode(rel))[0] AS tgt_label "
            "LIMIT 100"
        ).format(hops=hops)

        results = []
        with self._driver.session() as session:
            records = session.run(cypher, node_ids=node_ids)
            for rec in records:
                results.append({
                    "source":    rec["source"],
                    "relation":  rec["relation"],
                    "target":    rec["target"],
                    "src_label": rec["src_label"],
                    "tgt_label": rec["tgt_label"],
                })
        return results

    def get_project_full_context(self, project_id: str) -> list:
        """One-hop: all test cases, bugs, and requirements for a project."""
        if not self._driver:
            self._connect()
        cypher = (
            "MATCH (p:Project {_node_id: $pid})-[r]->(n) "
            "RETURN p._node_id AS source, type(r) AS relation, "
            "       n._node_id AS target, labels(n)[0] AS tgt_label "
            "LIMIT 200"
        )
        results = []
        with self._driver.session() as session:
            records = session.run(cypher, pid=project_id)
            for rec in records:
                results.append({
                    "source":    rec["source"],
                    "relation":  rec["relation"],
                    "target":    rec["target"],
                    "src_label": "Project",
                    "tgt_label": rec["tgt_label"],
                })
        return results

    def format_for_llm(self, paths: list) -> str:
        """Convert path list to readable text lines for LLM context."""
        if not paths:
            return ""
        lines = ["[Neo4j graph paths]"]
        for p in paths:
            lines.append(
                f"  {p['src_label']} {p['source']} "
                f"-[{p['relation']}]-> "
                f"{p.get('tgt_label', '')} {p['target']}"
            )
        return "\n".join(lines)
