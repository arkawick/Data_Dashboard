# GraphRAG Guide

This project implements a complete GraphRAG pipeline with two retrieval modes —
TF-IDF (keyword) and FAISS (semantic) — plus optional Neo4j 2-hop graph expansion.
All three query backends (dry-run, Claude, Ollama) are supported via the CLI, the REST API,
and the React frontend Query page.

---

## Architecture

```
MongoDB (5 collections)
        |
        v
build_graph.py  -->  NetworkX DiGraph  -->  graph.gpickle  (365 nodes, 1045 edges)
                                       -->  graph.json
        |
        v
chunk_graph.py  -->  1775 text chunks  -->  chunks.json
        |
        +-- [TF-IDF path]    retriever.py      -->  keyword scoring (default)
        |
        +-- [Semantic path]  embed_chunks.py   -->  all-MiniLM-L6-v2  -->  chunks.faiss
        |
        v
query.py / api.py  -->  retrieve top-K chunks  -->  LLM (Claude / Ollama / dry-run)
        |
        +-- [Hybrid path]  neo4j_retriever.py  -->  2-hop Cypher expansion
        |
        v
load_neo4j.py  -->  Neo4j (visualization + hybrid context)
        |
        v
React frontend (Query page)  -->  standard / hybrid / raw chunk search
```

`get_retriever()` in `retriever.py` automatically selects `SemanticRetriever` if `chunks.faiss` exists,
otherwise falls back to `GraphRetriever` (TF-IDF). No code change needed.

---

## Step 1 — Build the graph

```bash
python graphrag/build_graph.py
```

Reads all 5 MongoDB collections and builds a NetworkX `DiGraph`:
- Each document becomes a **node** with its full property set
- Each FK relationship becomes a **directed edge** with a `rel` attribute

Outputs:
- `graphrag/graph.gpickle` — binary NetworkX graph (fast reload)
- `graphrag/graph.json` — full node + edge catalogue with stats block

**Result:** 365 nodes, 1045 edges across 10 relationship types.

Environment variables (defaults work locally):
```bash
MONGO_URI=mongodb://localhost:27017/
DB_NAME=test_db
```

---

## Step 2 — Chunk the graph

```bash
python graphrag/chunk_graph.py
```

Converts every node and edge into natural-language text chunks.

### Three chunk types (1775 total)

**Entity chunks (365)** — one per node, full property description.

```
Bug BUG-042 'Auth token expiry not handled' is a Critical severity Security bug
with status 'Open' and priority P1. Found in project 'API Gateway' during test
'Validate_auth_refresh_019'. Reported by Alice Smith, assigned to Bob Jones.
Domain: Finance, team: Alpha.
```

**Relationship chunks (1045)** — one per edge, plain-English description.

```
Alice Smith (EMP-001) is assigned to fix bug 'Auth token expiry not handled' (BUG-042).
```

**Neighbourhood chunks (365)** — one per node, all direct connections listed.

```
Neighbourhood of Employee EMP-001 (Alice Smith):
  -> Project PROJ-003 (API Gateway) via [LEADS]
  -> TestCase TC-017 (Validate_login_flow_017) via [ASSIGNED_TO]
  -> Bug BUG-042 (Auth token expiry not handled) via [ASSIGNED_BUG]
  -> Requirement REQ-031 (The system shall support OAuth2) via [RESPONSIBLE_FOR]
```

Each chunk: `id`, `type`, `label`, `node_id` (or `source`/`target`), `text`, `keywords`.

---

## Step 3a — TF-IDF retrieval (no extra install)

Works out of the box. No embeddings, no external index.

```python
from graphrag.retriever import get_retriever
r = get_retriever()          # returns GraphRetriever (TF-IDF) if no FAISS index
chunks = r.retrieve("critical bugs in Finance", top_k=20)
```

Scoring: TF-IDF over chunk keywords. Fast, deterministic, no GPU/download required.

---

## Step 3b — FAISS semantic retrieval (recommended)

Replaces TF-IDF with sentence-transformer embeddings. Finds semantically similar chunks
even when exact keywords don't match (e.g. "defect" matches "bug").

### Build the index (run once)

```bash
pip install faiss-cpu sentence-transformers
python graphrag/embed_chunks.py
```

Outputs:
- `graphrag/chunks.faiss` — FAISS IndexFlatIP (cosine similarity via L2-normalised vectors)
- `graphrag/id_map.json` — FAISS integer index -> chunks list position

Model: `all-MiniLM-L6-v2` (384 dimensions, ~90MB, fast on CPU, downloads once to `~/.cache/huggingface`).

### Use it

```python
from graphrag.retriever import get_retriever
r = get_retriever()          # auto-selects SemanticRetriever when chunks.faiss exists
chunks = r.retrieve("defects found during regression testing", top_k=15)
```

No code change needed — `get_retriever()` picks the best available retriever automatically.

---

## Step 3c — Hybrid retrieval (FAISS + Neo4j)

Best retrieval quality. Combines:
1. FAISS semantic chunk search
2. Neo4j 2-hop Cypher expansion of matched nodes

```python
from graphrag.hybrid_retriever import HybridRetriever
hr = HybridRetriever()
result = hr.retrieve("critical bugs in Finance", top_k=15)

# result keys:
# "chunks"           - list of FAISS chunk dicts
# "graph_paths"      - list of {source, relation, target} from Neo4j
# "combined_context" - merged text ready for LLM prompt
```

Via the API:
```bash
curl -X POST http://localhost:8001/query/hybrid \
  -H "Content-Type: application/json" \
  -d '{"question": "Show path from employee to requirement via bugs", "top_k": 15}'
```

Fallback: if Neo4j is unavailable, returns chunks-only result with a warning.

---

## Step 4 — Query

### React frontend (recommended)

Open the **Query** page at `http://localhost:5173/query`.

Select a mode:
- **Standard** — TF-IDF or FAISS retrieval + LLM answer
- **Hybrid** — FAISS + Neo4j 2-hop + LLM answer
- **Chunks** — raw chunk search, no LLM call

Enter your question, click Send. Results appear in-page.

### CLI

```bash
python graphrag/query.py                              # interactive
python graphrag/query.py "Who leads critical projects?"  # single-shot
```

Backend auto-detection:

| Condition | Backend used |
|---|---|
| `ANTHROPIC_API_KEY` set | Claude (`claude-sonnet-4-6`) |
| `OLLAMA_MODEL` set | Ollama (local model) |
| Neither set | Dry-run (prints chunks + full prompt) |

**Claude:**
```bash
set ANTHROPIC_API_KEY=sk-ant-...
python graphrag/query.py
```

**Ollama:**
```bash
ollama serve                # separate terminal
set OLLAMA_MODEL=llama3
python graphrag/query.py
```

**Dry-run** (default — no API key needed):

Prints the retrieved chunks and the full prompt. Useful for verifying retrieval quality.

### REST API

```bash
# GET (browser-friendly)
curl "http://localhost:8001/query?q=which+employees+own+critical+bugs&top_k=10"

# POST
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"question": "critical bugs in Finance", "top_k": 20, "backend": "auto"}'

# Raw chunk search (no LLM)
curl "http://localhost:8001/chunks/search?q=security+requirements&top_k=5"
```

Full Swagger UI: `http://localhost:8001/docs`

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

## Step 5 — Neo4j visualization

Neo4j lets you browse the graph visually, click nodes, expand relationships, and run Cypher.

### Start Neo4j

```bash
# Docker (included in docker-compose.yml)
docker compose up -d neo4j

# Or standalone
docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j
```

### Load the graph

```bash
python graphrag/load_neo4j.py
```

Loads 365 nodes and 1045 relationships into Neo4j at `bolt://localhost:7687`.

Override connection via env vars:
```bash
set NEO4J_URI=bolt://localhost:7687
set NEO4J_USER=neo4j
set NEO4J_PASSWORD=password
```

### Open Neo4j Browser

`http://localhost:7474` — log in with `neo4j / password`.

**Start exploring:**
```cypher
MATCH (n) RETURN n LIMIT 100
```

---

## Cypher Query Reference

### Basic exploration

```cypher
// Node counts by label
MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count ORDER BY count DESC

// Relationship counts by type
MATCH ()-[r]->() RETURN type(r) AS rel, count(r) AS count ORDER BY count DESC
```

### Employee queries

```cypher
// Employees ranked by bugs assigned
MATCH (e:Employee)-[:ASSIGNED_BUG]->(b:Bug)
RETURN e.name, e.team, count(b) AS bugs_assigned ORDER BY bugs_assigned DESC

// Employees who reported AND are assigned to the same bug
MATCH (e:Employee)-[:REPORTED]->(b:Bug)<-[:ASSIGNED_BUG]-(e)
RETURN e.name, b.title, b.severity

// Senior employees and the projects they lead
MATCH (e:Employee {seniority: 'Senior'})-[:LEADS]->(p:Project)
RETURN e.name, p.project_name, p.status, p.priority
```

### Bug queries

```cypher
// Critical bugs and their projects
MATCH (p:Project)-[:HAS_BUG]->(b:Bug {severity: 'Critical'})
RETURN p.project_name, b.title, b.status ORDER BY p.project_name

// Projects ranked by critical bug count
MATCH (p:Project)-[:HAS_BUG]->(b:Bug {severity: 'Critical'})
RETURN p.project_name, count(b) AS critical_bugs ORDER BY critical_bugs DESC

// Open bugs with assignee and project
MATCH (e:Employee)-[:ASSIGNED_BUG]->(b:Bug {status: 'Open'})<-[:HAS_BUG]-(p:Project)
RETURN e.name, b.title, b.severity, p.project_name ORDER BY b.severity
```

### Test case queries

```cypher
// Failed test cases and their assignees
MATCH (e:Employee)-[:ASSIGNED_TO]->(tc:TestCase {status: 'Failed'})
RETURN e.name, tc.test_case_name, tc.test_type, tc.automation_status

// Test cases that found bugs
MATCH (tc:TestCase)-[:FOUND_BUG]->(b:Bug)
RETURN tc.test_case_name, b.title, b.severity ORDER BY b.severity

// Automated vs manual per project
MATCH (p:Project)-[:HAS_TEST_CASE]->(tc:TestCase)
RETURN p.project_name, tc.automation_status, count(tc) AS count
ORDER BY p.project_name
```

### Requirement queries

```cypher
// Requirements not covered by any test case
MATCH (r:Requirement)
WHERE NOT ()-[:COVERS]->(r)
RETURN r.requirement_id, r.requirement_name, r.priority, r.status

// Employee workload: requirements owned
MATCH (e:Employee)-[:RESPONSIBLE_FOR]->(r:Requirement)
RETURN e.name, e.department, count(r) AS requirements_owned
ORDER BY requirements_owned DESC
```

### Multi-hop queries

```cypher
// Full path: Employee leads Project with Critical bug
MATCH (e:Employee)-[:LEADS]->(p:Project)-[:HAS_BUG]->(b:Bug {severity: 'Critical'})
RETURN e.name, p.project_name, b.title, b.status

// 3-hop: Employee -> Bug <- TestCase -> Requirement
MATCH (e:Employee)-[:ASSIGNED_BUG]->(b:Bug)<-[:FOUND_BUG]-(tc:TestCase)-[:COVERS]->(r:Requirement)
RETURN e.name, b.title, tc.test_case_name, r.requirement_name LIMIT 10

// Visualize as path object
MATCH path = (e:Employee)-[:LEADS]->(p:Project)-[:HAS_TEST_CASE]->(tc:TestCase)-[:FOUND_BUG]->(b:Bug)
RETURN path LIMIT 10

// Domain subgraph
MATCH (n) WHERE n.domain = 'Finance' RETURN n LIMIT 50
```

---

## Retriever API Reference

```python
from graphrag.retriever import get_retriever

# Auto-selects SemanticRetriever (FAISS) if index exists, else GraphRetriever (TF-IDF)
r = get_retriever()

# Retrieve top-K chunks
chunks = r.retrieve("critical bugs in Finance", top_k=10)
chunks = r.retrieve("security requirements", top_k=5, chunk_types=["entity", "relationship"])

# Get formatted context string for LLM
context = r.get_context_text("who leads API Gateway", top_k=5)

# Fetch all chunks for a specific node/edge ID
chunks = r.retrieve_by_id("EMP-001")
chunks = r.retrieve_by_id("PROJ-003")
```

Force a specific retriever:
```python
from graphrag.retriever import GraphRetriever
from graphrag.semantic_retriever import SemanticRetriever

tfidf = GraphRetriever()        # always TF-IDF
semantic = SemanticRetriever()  # always FAISS (requires chunks.faiss)
```

---

## File Reference

| File | Description |
|---|---|
| `graphrag/build_graph.py` | MongoDB -> NetworkX DiGraph -> graph.gpickle + graph.json |
| `graphrag/chunk_graph.py` | Graph -> 1775 text chunks -> chunks.json |
| `graphrag/retriever.py` | TF-IDF GraphRetriever + `get_retriever()` factory |
| `graphrag/semantic_retriever.py` | FAISS SemanticRetriever (same interface as TF-IDF) |
| `graphrag/embed_chunks.py` | Build FAISS index (chunks.faiss + id_map.json) |
| `graphrag/neo4j_retriever.py` | Neo4j 2-hop Cypher context expansion |
| `graphrag/hybrid_retriever.py` | FAISS + Neo4j merged retriever |
| `graphrag/query.py` | Interactive CLI: dry-run / Claude / Ollama |
| `graphrag/api.py` | FastAPI REST API for all query modes |
| `graphrag/schemas.py` | Pydantic models for the FastAPI endpoints |
| `graphrag/tasks.py` | Celery tasks + nightly beat schedule |
| `graphrag/load_neo4j.py` | Load graph.gpickle into running Neo4j |
| `graphrag/graph.json` | Generated: node + edge catalogue with stats |
| `graphrag/graph.gpickle` | Generated: NetworkX binary |
| `graphrag/chunks.json` | Generated: 1775 text chunks |
| `graphrag/chunks.faiss` | Generated: FAISS semantic index |
| `graphrag/id_map.json` | Generated: FAISS int -> chunk index mapping |
