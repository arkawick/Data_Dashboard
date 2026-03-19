# GraphRAG Guide

This project includes a complete, working GraphRAG pipeline — no external vector database or
embedding model required. It uses TF-IDF retrieval over natural-language graph chunks and
supports three query backends: dry-run (no key), Claude API, and Ollama (local models).

It also supports loading the graph into **Neo4j** for visual exploration.

---

## Architecture Overview

```
MongoDB (5 collections)
        |
        v
build_graph.py  -->  NetworkX DiGraph  -->  graph.gpickle  (365 nodes, 1045 edges)
                                       -->  graph.json      (human-readable export)
        |
        v
chunk_graph.py  -->  Natural-language chunks  -->  chunks.json  (1775 chunks)
        |
        v
retriever.py    -->  TF-IDF index over chunk keywords
        |
        v
query.py        -->  User question  -->  retrieve top-K chunks  -->  LLM answer
        |
        v
load_neo4j.py   -->  Neo4j (optional, for visual graph browser)
```

---

## Step 1 — Build the graph

```bash
python graphrag/build_graph.py
```

Reads all 5 MongoDB collections and builds a NetworkX `DiGraph` where:
- Each document becomes a **node** with its full property set
- Each FK relationship becomes a **directed edge** with a `rel` attribute

Outputs:
- `graphrag/graph.gpickle` — binary NetworkX graph (fast reload)
- `graphrag/graph.json` — full node + edge catalogue (for inspection or Neo4j import)

**Result:** 365 nodes, 1045 edges across 10 relationship types.

---

## Step 2 — Chunk the graph

```bash
python graphrag/chunk_graph.py
```

Converts every node and edge in the graph into natural-language text chunks.

**Three chunk types generated:**

### Entity chunks (365 total)
One per node. Describes the entity using a template per node type.

Example (Bug):
```
Bug BUG-042 'Auth token expiry not handled' is a Critical severity Security bug
with status 'Open' and priority P1. Found in project 'API Gateway' during test
'Validate_auth_refresh_019'. Reported by Alice Smith, assigned to Bob Jones.
Domain: Finance, team: Alpha.
```

### Relationship chunks (1045 total)
One per edge. Describes the relationship in plain English.

Example:
```
Alice Smith (EMP-001) is assigned to fix bug 'Auth token expiry not handled' (BUG-042).
```

### Neighbourhood chunks (365 total)
One per node. Lists all direct neighbours (predecessors and successors) with their relationship types.

Example:
```
Neighbourhood of Employee EMP-001 (Alice Smith):
  -> Project PROJ-003 (API Gateway) via [LEADS]
  -> TestCase TC-017 (Validate_login_flow_017) via [ASSIGNED_TO]
  -> Bug BUG-042 (Auth token expiry not handled) via [ASSIGNED_BUG]
  -> Requirement REQ-031 (The system shall support OAuth2) via [RESPONSIBLE_FOR]
```

**Total: 1775 chunks** saved to `graphrag/chunks.json`.

Each chunk has: `id`, `type`, `label`, `node_id` (or `source`/`target`), `text`, `keywords`.

---

## Step 3 — Query

```bash
python graphrag/query.py
```

Or single-shot:
```bash
python graphrag/query.py "Which employees are assigned to critical bugs?"
```

### How retrieval works

1. The user question is tokenized into terms
2. Every chunk is scored using TF-IDF against the question terms
3. The top-K chunks (default: 20) are selected as context
4. Context is injected into a prompt and sent to the LLM

No vector embeddings or external index needed — the TF-IDF scorer is built in pure Python.

### Backends

**Dry-run (default — no API key needed)**

Prints the retrieved chunks and the full prompt that would be sent to an LLM.
Useful for verifying retrieval quality without spending API credits.

```bash
python graphrag/query.py "Which projects have the most critical bugs?"
```

**Claude**

```bash
set ANTHROPIC_API_KEY=sk-ant-...
python graphrag/query.py
```

Uses `claude-sonnet-4-6` by default. Change the `MODEL` constant in `query.py` to switch models.

**Ollama (local models)**

```bash
ollama serve                        # in a separate terminal
set OLLAMA_MODEL=llama3
python graphrag/query.py
```

Sends requests to `http://localhost:11434/api/generate`. Any model available in your Ollama
installation can be used.

### Example questions

```
Which employees are assigned to critical bugs?
Which project has the most open bugs?
List all requirements in the Finance domain and their verification owners.
Which test cases cover security requirements?
Who leads projects in the Healthcare domain?
Show all failed test cases assigned to senior engineers.
Which bugs were reported and also assigned to the same employee?
What is the status of requirements in the Platform Modernization project?
```

---

## Step 4 — Neo4j visualization

Neo4j lets you browse the graph visually, click on nodes, expand relationships, and run
Cypher queries.

### Setup

**Option A — Neo4j Desktop**
1. Download from https://neo4j.com/download/
2. Install, create a new project, add a local DBMS
3. Set a password and click **Start**

**Option B — Docker**
```bash
docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j
```

### Install the Python driver

```bash
pip install neo4j
```

### Load the graph

```bash
python graphrag/load_neo4j.py
```

Default connection: `bolt://localhost:7687`, user `neo4j`, password `password`.

To override:
```bash
set NEO4J_PASSWORD=yourpassword
python graphrag/load_neo4j.py
```

Or edit `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` at the top of `load_neo4j.py`.

**What it loads:**
- 365 nodes across 5 labels: `Employee`, `Project`, `TestCase`, `Bug`, `Requirement`
- 1045 relationships across 10 types
- All node properties (lists are serialised as comma-separated strings)

### Using Neo4j Browser

Open `http://localhost:7474` and log in.

**Starter query — see all nodes:**
```cypher
MATCH (n) RETURN n LIMIT 100
```

Click any node to expand its relationships. Use the left panel to color nodes by label.

---

## Cypher Query Reference

### Basic exploration

```cypher
-- Count nodes by label
MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count ORDER BY count DESC

-- Count relationships by type
MATCH ()-[r]->() RETURN type(r) AS rel, count(r) AS count ORDER BY count DESC

-- See all properties on a node type
MATCH (e:Employee) RETURN e LIMIT 5
```

### Employee queries

```cypher
-- All employees and how many bugs they are assigned to
MATCH (e:Employee)-[:ASSIGNED_BUG]->(b:Bug)
RETURN e.name, e.team, e.seniority, count(b) AS bugs_assigned
ORDER BY bugs_assigned DESC

-- Employees who both reported and are assigned to the same bug
MATCH (e:Employee)-[:REPORTED]->(b:Bug)<-[:ASSIGNED_BUG]-(e)
RETURN e.name, b.title, b.severity

-- Senior employees and the projects they lead
MATCH (e:Employee {seniority: 'Senior'})-[:LEADS]->(p:Project)
RETURN e.name, p.project_name, p.status, p.priority
```

### Bug queries

```cypher
-- Critical bugs and which projects they belong to
MATCH (p:Project)-[:HAS_BUG]->(b:Bug {severity: 'Critical'})
RETURN p.project_name, b.title, b.status, b.priority
ORDER BY p.project_name

-- Open bugs with their assignees and projects
MATCH (e:Employee)-[:ASSIGNED_BUG]->(b:Bug {status: 'Open'})<-[:HAS_BUG]-(p:Project)
RETURN e.name, b.title, b.severity, p.project_name
ORDER BY b.severity

-- Projects ranked by critical bug count
MATCH (p:Project)-[:HAS_BUG]->(b:Bug {severity: 'Critical'})
RETURN p.project_name, count(b) AS critical_bugs
ORDER BY critical_bugs DESC
```

### Test case queries

```cypher
-- Failed test cases and who they are assigned to
MATCH (e:Employee)-[:ASSIGNED_TO]->(tc:TestCase {status: 'Failed'})
RETURN e.name, tc.test_case_name, tc.test_type, tc.automation_status

-- Test cases that found bugs, with bug severity
MATCH (tc:TestCase)-[:FOUND_BUG]->(b:Bug)
RETURN tc.test_case_name, b.title, b.severity, b.status
ORDER BY b.severity

-- Automated vs manual test counts per project
MATCH (p:Project)-[:HAS_TEST_CASE]->(tc:TestCase)
RETURN p.project_name, tc.automation_status, count(tc) AS count
ORDER BY p.project_name, tc.automation_status
```

### Requirement queries

```cypher
-- Requirements not covered by any test case
MATCH (r:Requirement)
WHERE NOT ()-[:COVERS]->(r)
RETURN r.requirement_id, r.requirement_name, r.priority, r.status

-- Requirements by category and status
MATCH (r:Requirement)
RETURN r.category, r.status, count(r) AS count
ORDER BY r.category, r.status

-- Employee workload: requirements they are responsible for
MATCH (e:Employee)-[:RESPONSIBLE_FOR]->(r:Requirement)
RETURN e.name, e.department, count(r) AS requirements_owned
ORDER BY requirements_owned DESC
```

### Multi-hop / path queries

```cypher
-- Full path: Employee leads Project which has a Critical bug
MATCH (e:Employee)-[:LEADS]->(p:Project)-[:HAS_BUG]->(b:Bug {severity: 'Critical'})
RETURN e.name, p.project_name, b.title, b.status

-- 3-hop: Employee -> Bug <- TestCase -> Requirement
MATCH (e:Employee)-[:ASSIGNED_BUG]->(b:Bug)<-[:FOUND_BUG]-(tc:TestCase)-[:COVERS]->(r:Requirement)
RETURN e.name, b.title, tc.test_case_name, r.requirement_name
LIMIT 10

-- Full path as graph object (visualize in browser)
MATCH path = (e:Employee)-[:LEADS]->(p:Project)-[:HAS_TEST_CASE]->(tc:TestCase)-[:FOUND_BUG]->(b:Bug)
RETURN path LIMIT 10

-- Domain-specific subgraph: all nodes in Finance domain
MATCH (n)
WHERE n.domain = 'Finance'
RETURN n LIMIT 50
```

---

## Retriever API (Python)

Use the retriever directly in your own code:

```python
from graphrag.retriever import GraphRetriever

r = GraphRetriever()                          # loads chunks.json, builds TF-IDF index

# Retrieve top-K chunks for a query
chunks = r.retrieve("critical bugs in finance domain", top_k=10)
for c in chunks:
    print(f"[{c['type']}] {c['text'][:100]}")

# Get context as a single string for LLM injection
context = r.get_context_text("who leads the API Gateway project", top_k=5)

# Fetch all chunks associated with a specific node or edge
chunks = r.retrieve_by_id("EMP-001")
```

---

## File Reference

| File | Description |
|---|---|
| `graphrag/build_graph.py` | Loads MongoDB -> NetworkX DiGraph, exports graph.json + graph.gpickle |
| `graphrag/chunk_graph.py` | Converts graph to 1775 text chunks, saves chunks.json |
| `graphrag/retriever.py` | TF-IDF retriever; `GraphRetriever` class |
| `graphrag/query.py` | Interactive CLI query interface; auto-detects Claude/Ollama/dry-run |
| `graphrag/load_neo4j.py` | Loads graph into running Neo4j instance |
| `graphrag/graph.json` | Full node + edge catalogue (generated) |
| `graphrag/graph.gpickle` | NetworkX binary graph (generated) |
| `graphrag/chunks.json` | 1775 text chunks with keywords (generated) |

---

## Recommended Stack for Production GraphRAG

| Component | Tool |
|---|---|
| Graph DB | Neo4j Desktop (free) or AuraDB (cloud free tier) |
| In-memory graph | NetworkX (this project) |
| Vector index | FAISS or Chroma (replace TF-IDF for semantic search) |
| Embedding model | `voyage-3` (Voyage AI) or `text-embedding-3-small` (OpenAI) |
| LLM | Claude API (`claude-sonnet-4-6`) |
| GraphRAG framework | LlamaIndex Knowledge Graph Index or Microsoft GraphRAG |
