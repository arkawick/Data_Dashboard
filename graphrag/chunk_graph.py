"""
graphrag/chunk_graph.py
=======================
Converts the NetworkX graph into natural-language text chunks
suitable for vector indexing and LLM context retrieval.

Three chunk types are generated:
  entity       — one chunk per node (describes the entity)
  relationship — one chunk per edge (describes the relationship)
  neighborhood — one chunk per node listing all its neighbours

Output:  graphrag/chunks.json

Run:
    python graphrag/chunk_graph.py
"""

import json
import os
import pickle
import re

GRAPH_PICKLE = os.path.join(os.path.dirname(__file__), "graph.gpickle")
CHUNKS_PATH  = os.path.join(os.path.dirname(__file__), "chunks.json")


# ── entity templates ─────────────────────────────────────────────────────────
def chunk_employee(props):
    skills = props.get("skills", "")
    if isinstance(skills, list):
        skills = ", ".join(skills)
    return (
        f"Employee {props['employee_id']} named {props.get('name', 'Unknown')} "
        f"is a {props.get('seniority', '')} {props.get('role', '')} "
        f"in the {props.get('department', '')} department, "
        f"team {props.get('team', '')}, based in {props.get('location', '')}. "
        f"Skills: {skills}. Status: {props.get('db_status', '')}."
    )


def chunk_project(props):
    stack = props.get("tech_stack", "")
    if isinstance(stack, list):
        stack = ", ".join(stack)
    return (
        f"Project {props['project_id']} '{props.get('project_name', '')}' "
        f"is a {props.get('priority', '')} priority project "
        f"with status '{props.get('status', '')}' "
        f"in the {props.get('domain', '')} domain. "
        f"Led by {props.get('lead_name', 'N/A')}, team {props.get('team', '')}. "
        f"Tech stack: {stack}. Git hash: {props.get('git_hash', '')}."
    )


def chunk_testcase(props):
    return (
        f"Test case {props['test_case_id']} '{props.get('test_case_name', '')}' "
        f"is a {props.get('test_type', '')} test with status '{props.get('status', '')}'. "
        f"Automation: {props.get('automation_status', '')}. "
        f"Assigned to: {props.get('assigned_to_name', 'N/A')}. "
        f"Folder: {props.get('parent_folder', '')} -> {props.get('path_folder', '')}. "
        f"Domain: {props.get('domain', '')}, team: {props.get('team', '')}. "
        f"Project: {props.get('project_name', 'N/A')}."
    )


def chunk_bug(props):
    return (
        f"Bug {props['bug_id']} '{props.get('title', '')}' "
        f"is a {props.get('severity', '')} severity {props.get('bug_type', '')} bug "
        f"with status '{props.get('status', '')}' and priority {props.get('priority', '')}. "
        f"Found in project '{props.get('project_name', 'N/A')}' "
        f"during test '{props.get('test_case_name', 'N/A')}'. "
        f"Reported by {props.get('reporter_name', 'N/A')}, "
        f"assigned to {props.get('assignee_name', 'N/A')}. "
        f"Domain: {props.get('domain', '')}, team: {props.get('team', '')}."
    )


def chunk_requirement(props):
    return (
        f"Requirement {props['requirement_id']} states: '{props.get('requirement_name', '')}'. "
        f"Category: {props.get('category', '')}, priority: {props.get('priority', '')}, "
        f"status: '{props.get('status', '')}'. "
        f"Part of project '{props.get('project_name', 'N/A')}', "
        f"domain: {props.get('domain', '')}, team: {props.get('team', '')}. "
        f"Covered by test '{props.get('covered_by_test_case_name', 'N/A')}'. "
        f"Verified by: {props.get('verification_responsibility', 'N/A')}. "
        f"DB status: {props.get('db_status', '')}."
    )


ENTITY_CHUNKERS = {
    "Employee":    chunk_employee,
    "Project":     chunk_project,
    "TestCase":    chunk_testcase,
    "Bug":         chunk_bug,
    "Requirement": chunk_requirement,
}


# ── relationship templates ────────────────────────────────────────────────────
REL_TEMPLATES = {
    "LEADS":           "{src_name} ({src}) leads the project '{tgt_name}' ({tgt}).",
    "ASSIGNED_TO":     "{src_name} ({src}) is assigned to test case '{tgt_name}' ({tgt}).",
    "REPORTED":        "{src_name} ({src}) reported bug '{tgt_name}' ({tgt}).",
    "ASSIGNED_BUG":    "{src_name} ({src}) is assigned to fix bug '{tgt_name}' ({tgt}).",
    "RESPONSIBLE_FOR": "{src_name} ({src}) is responsible for verifying requirement '{tgt_name}' ({tgt}).",
    "HAS_TEST_CASE":   "Project '{src_name}' ({src}) has test case '{tgt_name}' ({tgt}).",
    "HAS_BUG":         "Project '{src_name}' ({src}) has bug '{tgt_name}' ({tgt}).",
    "HAS_REQUIREMENT": "Project '{src_name}' ({src}) has requirement '{tgt_name}' ({tgt}).",
    "FOUND_BUG":       "Test case '{src_name}' ({src}) found bug '{tgt_name}' ({tgt}).",
    "COVERS":          "Test case '{src_name}' ({src}) covers requirement '{tgt_name}' ({tgt}).",
}


def node_name(G, node_id):
    p = G.nodes[node_id]
    return (
        p.get("name") or p.get("project_name") or p.get("test_case_name") or
        p.get("title") or p.get("requirement_name") or node_id
    )


def keywords(text):
    """Extract lowercase word tokens from text."""
    return list(set(re.findall(r"[a-z0-9\-]+", text.lower())))


# ── build chunks ─────────────────────────────────────────────────────────────
def build_chunks(G):
    chunks = []

    # 1. Entity chunks
    for node_id, props in G.nodes(data=True):
        label   = props.get("label", "")
        chunker = ENTITY_CHUNKERS.get(label)
        if not chunker:
            continue
        text = chunker(props)
        chunks.append({
            "id":       f"entity:{node_id}",
            "type":     "entity",
            "label":    label,
            "node_id":  node_id,
            "text":     text,
            "keywords": keywords(text),
        })

    # 2. Relationship chunks
    for u, v, edge_props in G.edges(data=True):
        rel      = edge_props.get("rel", "RELATED_TO")
        template = REL_TEMPLATES.get(rel, "{src} --[{rel}]--> {tgt}")
        src_name = node_name(G, u)
        tgt_name = node_name(G, v)
        text = template.format(src=u, tgt=v, src_name=src_name, tgt_name=tgt_name, rel=rel)
        chunks.append({
            "id":       f"rel:{u}:{v}",
            "type":     "relationship",
            "rel":      rel,
            "source":   u,
            "target":   v,
            "text":     text,
            "keywords": keywords(text),
        })

    # 3. Neighbourhood chunks (node + all direct neighbours)
    for node_id, props in G.nodes(data=True):
        label = props.get("label", "")
        preds = list(G.predecessors(node_id))
        succs = list(G.successors(node_id))
        if not preds and not succs:
            continue

        lines = [f"Neighbourhood of {label} {node_id} ({node_name(G, node_id)}):"]
        for p in preds:
            rel = G.edges[p, node_id].get("rel", "?")
            lines.append(f"  <- {G.nodes[p].get('label','')} {p} ({node_name(G, p)}) via [{rel}]")
        for s in succs:
            rel = G.edges[node_id, s].get("rel", "?")
            lines.append(f"  -> {G.nodes[s].get('label','')} {s} ({node_name(G, s)}) via [{rel}]")

        text = "\n".join(lines)
        chunks.append({
            "id":           f"nbr:{node_id}",
            "type":         "neighborhood",
            "label":        label,
            "node_id":      node_id,
            "in_degree":    len(preds),
            "out_degree":   len(succs),
            "text":         text,
            "keywords":     keywords(text),
        })

    return chunks


def main():
    print(f"Loading graph from {GRAPH_PICKLE}...")
    with open(GRAPH_PICKLE, "rb") as f:
        G = pickle.load(f)
    print(f"  {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    print("Generating chunks...")
    chunks = build_chunks(G)

    entity_count = sum(1 for c in chunks if c["type"] == "entity")
    rel_count    = sum(1 for c in chunks if c["type"] == "relationship")
    nbr_count    = sum(1 for c in chunks if c["type"] == "neighborhood")
    print(f"  {entity_count} entity chunks")
    print(f"  {rel_count} relationship chunks")
    print(f"  {nbr_count} neighbourhood chunks")
    print(f"  {len(chunks)} total")

    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {CHUNKS_PATH}")


if __name__ == "__main__":
    main()
