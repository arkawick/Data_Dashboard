"""
graphrag/load_neo4j.py
======================
Loads the NetworkX graph into Neo4j for visualization.

Requirements:
    pip install neo4j

Setup:
    1. Install Neo4j Desktop: https://neo4j.com/download/
       OR run via Docker:
           docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j
    2. Start Neo4j and note your password
    3. Set credentials below (or via env vars NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    4. Run: python graphrag/load_neo4j.py

After loading, open http://localhost:7474 in your browser.
Type in the Neo4j Browser:
    MATCH (n) RETURN n LIMIT 100
"""

import os
import pickle

from neo4j import GraphDatabase

# ── connection config (override with env vars) ────────────────────────────────
NEO4J_URI      = os.environ.get("NEO4J_URI",      "bolt://localhost:7687")
NEO4J_USER     = os.environ.get("NEO4J_USER",     "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")

GRAPH_PICKLE = os.path.join(os.path.dirname(__file__), "graph.gpickle")

# Node label -> its primary ID field
NODE_ID_FIELDS = {
    "Employee":    "employee_id",
    "Project":     "project_id",
    "TestCase":    "test_case_id",
    "Bug":         "bug_id",
    "Requirement": "requirement_id",
}


def clean_props(props):
    """Convert lists to strings and drop None values for Neo4j compatibility."""
    clean = {}
    for k, v in props.items():
        if v is None:
            continue
        if isinstance(v, list):
            clean[k] = ", ".join(str(x) for x in v)
        else:
            clean[k] = v
    return clean


def load_graph():
    print(f"Loading graph from {GRAPH_PICKLE}...")
    with open(GRAPH_PICKLE, "rb") as f:
        G = pickle.load(f)
    print(f"  {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


def clear_db(session):
    print("Clearing existing Neo4j data...")
    session.run("MATCH (n) DETACH DELETE n")


def create_nodes(session, G):
    print("Creating nodes...")
    counts = {}
    for node_id, props in G.nodes(data=True):
        label = props.get("label", "Unknown")
        clean = clean_props({k: v for k, v in props.items() if k != "label"})
        clean["_node_id"] = node_id  # always store original ID

        cypher = f"CREATE (n:{label} $props)"
        session.run(cypher, props=clean)
        counts[label] = counts.get(label, 0) + 1

    for label, n in sorted(counts.items()):
        print(f"  {label:<15} {n} nodes")


def create_indexes(session):
    """Speed up relationship creation by indexing _node_id on each label."""
    print("Creating indexes...")
    for label in NODE_ID_FIELDS:
        session.run(f"CREATE INDEX IF NOT EXISTS FOR (n:{label}) ON (n._node_id)")


def create_relationships(session, G):
    print("Creating relationships...")
    counts = {}
    for u, v, edge_props in G.edges(data=True):
        rel = edge_props.get("rel", "RELATED_TO")
        src_label = G.nodes[u].get("label", "Unknown")
        tgt_label = G.nodes[v].get("label", "Unknown")

        cypher = (
            f"MATCH (a:{src_label} {{_node_id: $src}}), "
            f"(b:{tgt_label} {{_node_id: $tgt}}) "
            f"CREATE (a)-[:{rel}]->(b)"
        )
        session.run(cypher, src=u, tgt=v)
        counts[rel] = counts.get(rel, 0) + 1

    for rel, n in sorted(counts.items()):
        print(f"  {rel:<22} {n}")


def print_sample_queries():
    print("\n" + "=" * 60)
    print("Neo4j loaded! Open http://localhost:7474")
    print("=" * 60)
    print("\nSample Cypher queries to try in the Browser:\n")

    queries = [
        ("See all nodes (limited)",
         "MATCH (n) RETURN n LIMIT 100"),
        ("Employees and the bugs they are assigned to",
         "MATCH (e:Employee)-[:ASSIGNED_BUG]->(b:Bug) RETURN e.name, b.title, b.severity"),
        ("Critical bugs and their projects",
         "MATCH (p:Project)-[:HAS_BUG]->(b:Bug {severity:'Critical'}) RETURN p.project_name, b.title"),
        ("Who leads each project",
         "MATCH (e:Employee)-[:LEADS]->(p:Project) RETURN e.name, p.project_name, p.status"),
        ("Test cases that found bugs",
         "MATCH (tc:TestCase)-[:FOUND_BUG]->(b:Bug) RETURN tc.test_case_name, b.title, b.severity LIMIT 20"),
        ("Full 3-hop: Employee -> Bug <- TestCase -> Requirement",
         "MATCH (e:Employee)-[:ASSIGNED_BUG]->(b:Bug)<-[:FOUND_BUG]-(tc:TestCase)-[:COVERS]->(r:Requirement)\n"
         "RETURN e.name, b.title, tc.test_case_name, r.requirement_name LIMIT 10"),
    ]

    for title, q in queries:
        print(f"// {title}")
        print(q)
        print()


def main():
    G = load_graph()

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        driver.verify_connectivity()
        print(f"Connected to Neo4j at {NEO4J_URI}")
    except Exception as e:
        print(f"\nERROR: Could not connect to Neo4j.")
        print(f"  URI:  {NEO4J_URI}")
        print(f"  Make sure Neo4j is running and the password is correct.")
        print(f"  Details: {e}")
        return

    with driver.session() as session:
        clear_db(session)
        create_indexes(session)
        create_nodes(session, G)
        create_relationships(session, G)

    driver.close()
    print_sample_queries()


if __name__ == "__main__":
    main()
