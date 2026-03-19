"""
graphrag/build_graph.py
=======================
Loads all 5 MongoDB collections into a NetworkX directed graph,
then exports two files:
  graphrag/graph.json   — full node + edge catalogue (for inspection / Neo4j import)
  graphrag/graph.gpickle — NetworkX binary (fast reload in other scripts)

Run:
    python graphrag/build_graph.py
"""

import json
import os
import pickle
from datetime import datetime

import networkx as nx
from pymongo import MongoClient

MONGO_URI  = "mongodb://localhost:27017/"
DB_NAME    = "test_db"
OUT_DIR    = os.path.dirname(os.path.abspath(__file__))
JSON_PATH  = os.path.join(OUT_DIR, "graph.json")
PICKLE_PATH = os.path.join(OUT_DIR, "graph.gpickle")


# ── helpers ───────────────────────────────────────────────────────────────────
def clean(doc):
    """Strip MongoDB _id and convert datetime to ISO string."""
    return {
        k: (v.isoformat() if isinstance(v, datetime) else v)
        for k, v in doc.items()
        if k != "_id"
    }


def add_node(G, node_id, label, props):
    G.add_node(node_id, label=label, **props)


def add_edge(G, src, dst, rel, props=None):
    if src and dst and src in G and dst in G:
        G.add_edge(src, dst, rel=rel, **(props or {}))
        return True
    return False


# ── main ──────────────────────────────────────────────────────────────────────
def build():
    db = MongoClient(MONGO_URI)[DB_NAME]
    G  = nx.DiGraph()

    # ── NODES ─────────────────────────────────────────────────────────────────
    print("Loading nodes...")

    for doc in db.employees.find():
        d = clean(doc)
        add_node(G, d["employee_id"], "Employee", d)

    for doc in db.projects.find():
        d = clean(doc)
        add_node(G, d["project_id"], "Project", d)

    for doc in db.test_cases.find():
        d = clean(doc)
        add_node(G, d["test_case_id"], "TestCase", d)

    for doc in db.bugs.find():
        d = clean(doc)
        add_node(G, d["bug_id"], "Bug", d)

    for doc in db.requirements.find():
        d = clean(doc)
        add_node(G, d["requirement_id"], "Requirement", d)

    print(f"  {G.number_of_nodes()} nodes loaded")

    # ── EDGES ─────────────────────────────────────────────────────────────────
    print("Building edges...")
    counts = {}

    def track(rel, ok):
        if ok:
            counts[rel] = counts.get(rel, 0) + 1

    for doc in db.projects.find():
        d = clean(doc)
        track("LEADS",           add_edge(G, d.get("lead_employee_id"),          d["project_id"],    "LEADS"))

    for doc in db.test_cases.find():
        d = clean(doc)
        track("HAS_TEST_CASE",   add_edge(G, d.get("project_id"),                d["test_case_id"],  "HAS_TEST_CASE"))
        track("ASSIGNED_TO",     add_edge(G, d.get("assigned_to_employee_id"),   d["test_case_id"],  "ASSIGNED_TO"))

    for doc in db.bugs.find():
        d = clean(doc)
        track("HAS_BUG",         add_edge(G, d.get("project_id"),                d["bug_id"],        "HAS_BUG"))
        track("FOUND_BUG",       add_edge(G, d.get("test_case_id"),              d["bug_id"],        "FOUND_BUG"))
        track("REPORTED",        add_edge(G, d.get("reporter_employee_id"),      d["bug_id"],        "REPORTED"))
        track("ASSIGNED_BUG",    add_edge(G, d.get("assignee_employee_id"),      d["bug_id"],        "ASSIGNED_BUG"))

    for doc in db.requirements.find():
        d = clean(doc)
        track("HAS_REQUIREMENT", add_edge(G, d.get("project_id"),                d["requirement_id"],"HAS_REQUIREMENT"))
        track("COVERS",          add_edge(G, d.get("covered_by_test_case_id"),   d["requirement_id"],"COVERS"))
        track("RESPONSIBLE_FOR", add_edge(G, d.get("verifier_employee_id"),      d["requirement_id"],"RESPONSIBLE_FOR"))

    print(f"  {G.number_of_edges()} edges built")
    for rel, n in sorted(counts.items()):
        print(f"    {rel:<20} {n}")

    # ── EXPORT ────────────────────────────────────────────────────────────────
    # JSON
    graph_json = {
        "nodes": [
            {"id": n, **{k: v for k, v in G.nodes[n].items()}}
            for n in G.nodes
        ],
        "edges": [
            {"source": u, "target": v, **G.edges[u, v]}
            for u, v in G.edges
        ],
        "stats": {
            "nodes": G.number_of_nodes(),
            "edges": G.number_of_edges(),
            "edge_types": counts,
        },
    }
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(graph_json, f, indent=2, default=str)
    print(f"\nSaved: {JSON_PATH}")

    # Pickle
    with open(PICKLE_PATH, "wb") as f:
        pickle.dump(G, f)
    print(f"Saved: {PICKLE_PATH}")

    return G


if __name__ == "__main__":
    build()
