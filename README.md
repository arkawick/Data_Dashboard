# GraphRAG Data Dashboard

A full-stack data engineering project featuring:
- **MongoDB** — 5 interconnected collections forming a property graph (365 nodes, 1045 edges)
- **Django** — web dashboard with filters, joins, sort, search, and CSV export
- **GraphRAG pipeline** — NetworkX graph, TF-IDF retrieval, LLM query interface
- **Neo4j** — visual graph browser with Cypher queries
- **Excel uploaders** — GUI, CLI batch, and compare-and-sync scripts

---

## Prerequisites

```bash
pip install django pymongo openpyxl networkx neo4j anthropic
```

- MongoDB running on `localhost:27017`
- Python 3.10+

---

## Quick Start

### Step 1 — Generate data

```bash
python generate_data.py
```

Inserts 25 employees, 10 projects, 100 test cases, 150 bugs, 80 requirements into MongoDB with consistent foreign-key relationships.

### Step 2 — Run the Django dashboard

```bash
cd Django_Dashboard
python manage.py runserver
```

Open `http://127.0.0.1:8000/`

### Step 3 — Build and query the graph (optional)

```bash
python graphrag/build_graph.py     # MongoDB -> NetworkX graph (365 nodes, 1045 edges)
python graphrag/chunk_graph.py     # Graph -> 1775 text chunks
python graphrag/query.py           # Interactive query CLI (works without API key)
```

### Step 4 — Load into Neo4j for visualization (optional)

```bash
python graphrag/load_neo4j.py      # Loads graph into Neo4j
# Open http://localhost:7474
```

---

## Project Structure

```
Data_Dashboard/
|
+-- generate_data.py              # Generates randomized data directly into MongoDB
+-- generate_excel.py             # Generates randomized data as Excel files
+-- config.py                     # Maps Excel filenames -> MongoDB collections
+-- uploader.py                   # Tkinter GUI uploader (Excel -> MongoDB)
+-- run.bat                       # One-click launcher (Django + browser + uploader)
|
+-- input_folder/                 # Excel files read by uploader
|   +-- employees_data.xlsx
|   +-- projects_data.xlsx
|   +-- test_cases_data.xlsx
|   +-- bugs_data.xlsx
|   +-- requirements_data.xlsx
|
+-- Django_Dashboard/             # Django project root
|   +-- manage.py
|   +-- config/                   # Django config package (settings, urls, wsgi)
|   |   +-- settings.py
|   |   +-- urls.py
|   |   +-- wsgi.py
|   +-- dashboard/                # Django app
|       +-- views.py              # /index/  -- Projects, TestCases, Bugs
|       +-- views2.py             # /index2/ -- Requirements, Employees
|       +-- mongo_utils.py        # MongoDB connection helper
|       +-- templates/
|       |   +-- home.html         # Landing page
|       |   +-- index.html        # Projects/TestCases/Bugs dashboard
|       |   +-- index2.html       # Requirements/Employees dashboard
|       +-- static/
|           +-- style.css
|
+-- graphrag/                     # GraphRAG pipeline
|   +-- build_graph.py            # MongoDB -> NetworkX DiGraph -> graph.gpickle
|   +-- chunk_graph.py            # Graph -> natural-language chunks -> chunks.json
|   +-- retriever.py              # TF-IDF retriever over chunks
|   +-- query.py                  # Interactive query CLI (Claude / Ollama / dry-run)
|   +-- load_neo4j.py             # Loads graph into Neo4j for visualization
|   +-- graph.json                # Full node+edge catalogue (generated)
|   +-- graph.gpickle             # NetworkX binary (generated)
|   +-- chunks.json               # 1775 text chunks (generated)
|
+-- Uploader_Scripts/
|   +-- Base_Uploader_Scripts/    # Clear-and-insert scripts
|   |   +-- upload_all.py         # Batch: uploads all 5 collections at once
|   |   +-- employees_to_db.py
|   |   +-- projects_to_db.py
|   |   +-- test_cases_to_db.py
|   |   +-- bugs_to_db.py
|   |   +-- requirements_to_db.py
|   +-- Comp_Uploader_Scripts/    # Compare-and-update scripts (tracks db_status)
|       +-- employees_comp.py
|       +-- projects_comp.py
|       +-- test_cases_comp.py
|       +-- bugs_comp.py
|       +-- requirements_comp.py
|
+-- docs/
    +-- schema.md                 # Full field-level schema for all 5 collections
    +-- uploader_guide.md         # Excel upload workflow and script reference
    +-- graphrag_guide.md         # GraphRAG pipeline + Neo4j visualization guide
```

---

## Data Model

5 node types, 10 directed edge types, 365 nodes, 1045 edges total.

```
(Employee)    -[:LEADS]-------------> (Project)       via lead_employee_id
(Employee)    -[:ASSIGNED_TO]-------> (TestCase)      via assigned_to_employee_id
(Employee)    -[:REPORTED]----------> (Bug)           via reporter_employee_id
(Employee)    -[:ASSIGNED_BUG]------> (Bug)           via assignee_employee_id
(Employee)    -[:RESPONSIBLE_FOR]---> (Requirement)   via verifier_employee_id
(Project)     -[:HAS_TEST_CASE]-----> (TestCase)      via project_id
(Project)     -[:HAS_BUG]-----------> (Bug)           via project_id
(Project)     -[:HAS_REQUIREMENT]---> (Requirement)   via project_id
(TestCase)    -[:FOUND_BUG]---------> (Bug)           via test_case_id
(TestCase)    -[:COVERS]------------> (Requirement)   via covered_by_test_case_id
```

See [`docs/schema.md`](docs/schema.md) for full field-level detail.

---

## Dashboard URLs

| URL | Content |
|---|---|
| `http://127.0.0.1:8000/` | Home / landing page |
| `http://127.0.0.1:8000/index/` | Projects, Test Cases, Bugs + joined views |
| `http://127.0.0.1:8000/index2/` | Requirements, Employees + joined view |
| `http://127.0.0.1:8000/filter_by_domain/` | JSON API -- filter by domain |

Each page: column sort, live search, domain/team/status/date filters, CSV export.

---

## GraphRAG Query Modes

Set environment variable to choose backend:

| Mode | Setup | Command |
|---|---|---|
| Dry-run (default) | No key needed | `python graphrag/query.py` |
| Claude | `set ANTHROPIC_API_KEY=sk-ant-...` | `python graphrag/query.py` |
| Ollama | `set OLLAMA_MODEL=llama3` + run `ollama serve` | `python graphrag/query.py` |

---

## Docs

| File | Description |
|---|---|
| [`docs/schema.md`](docs/schema.md) | Full field-level schema for all 5 collections + graph edges |
| [`docs/uploader_guide.md`](docs/uploader_guide.md) | All upload methods, routing, sync vs insert |
| [`docs/graphrag_guide.md`](docs/graphrag_guide.md) | GraphRAG pipeline, Neo4j setup, Cypher queries |
| [`docs/future_steps.md`](docs/future_steps.md) | Production upgrade path — Docker, FastAPI, FAISS, Airflow, Kafka, observability |
