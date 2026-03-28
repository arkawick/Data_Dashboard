# GraphRAG Data Dashboard

A production-grade GraphRAG system: MongoDB data store, Django REST API, FastAPI query engine,
React SPA frontend, Neo4j graph database, FAISS semantic search, Celery async workers,
Airflow scheduling, Prometheus + Grafana observability, and full CI/CD via GitHub Actions and Jenkins.

**Graph:** 365 nodes, 1045 edges, 5 node types, 10 relationship types
**Chunks:** 1775 text chunks (entity + relationship + neighbourhood)
**Retrieval:** TF-IDF keyword or FAISS semantic (all-MiniLM-L6-v2) or Hybrid (FAISS + Neo4j 2-hop)
**Query backends:** Dry-run, Claude API, Ollama
**Frontend:** React 19 + TypeScript + Vite + TanStack Query + Recharts + Radix UI
**Deployment:** Docker Compose (one command) or local dev

---

## Quick Start

### Option A — Docker Compose (recommended)

```bash
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY if you have one
docker compose up -d
python generate_data.py
python graphrag/build_graph.py && python graphrag/chunk_graph.py
```

Then open `http://localhost:5173` (or build the frontend for production).

### Option B — Local dev (infrastructure via Docker, apps local)

```bash
# 1. Start infrastructure
docker compose up -d mongo neo4j redis prometheus grafana

# 2. Install backend dependencies
pip install -r requirements.txt
pip install -r Django_Dashboard/requirements.txt

# 3. Seed + build graph
python generate_data.py
python graphrag/build_graph.py
python graphrag/chunk_graph.py

# 4. (Optional) Build FAISS semantic index
python graphrag/embed_chunks.py

# 5. Run backend services
cd Django_Dashboard && python manage.py runserver 8000
# in another terminal:
uvicorn graphrag.api:app --reload --port 8001
# in another terminal:
celery -A graphrag.tasks worker --loglevel=info --pool=solo

# 6. Create first admin user
cd Django_Dashboard && python manage.py shell
>>> from dashboard.auth_views import create_user
>>> create_user("admin", "changeme", role="admin")

# 7. Run React frontend
cd frontend && npm install && npm run dev
# opens at http://localhost:5173
```

---

## Service URLs

| Service | URL | Credentials |
|---|---|---|
| React Frontend | `http://localhost:5173` | admin / changeme (default) |
| Django Dashboard (legacy) | `http://localhost:8000` | — |
| FastAPI Docs | `http://localhost:8001/docs` | none |
| Neo4j Browser | `http://localhost:7474` | neo4j / password |
| Grafana | `http://localhost:3001` | admin / admin |
| Prometheus | `http://localhost:9090` | none |
| Airflow | `http://localhost:8080` | admin / admin |

---

## Project Structure

```
Data_Dashboard/
|
+-- generate_data.py              # Seed MongoDB (25 emp, 10 proj, 100 tc, 150 bugs, 80 req)
+-- generate_excel.py             # Export MongoDB data to Excel files
+-- config.py                     # Excel filename -> MongoDB collection routing table
+-- uploader.py                   # Tkinter GUI uploader (Excel -> MongoDB)
+-- docker-compose.yml            # All services: mongo, neo4j, redis, django, fastapi,
|                                 #   celery, prometheus, grafana, airflow
+-- Dockerfile                    # FastAPI + Celery service image (context: project root)
+-- requirements.txt              # GraphRAG + FastAPI + Celery dependencies
+-- Jenkinsfile                   # Jenkins declarative CI/CD pipeline
+-- .env.example                  # Environment variable template
+-- .gitignore
|
+-- Django_Dashboard/
|   +-- manage.py
|   +-- Dockerfile                # Django service image
|   +-- requirements.txt          # Django-specific dependencies
|   +-- config/
|   |   +-- settings.py           # Env-var-aware: SECRET_KEY, DEBUG, CORS, Prometheus
|   |   +-- urls.py               # Dashboard routes + /api/* REST + /metrics
|   |   +-- wsgi.py
|   +-- dashboard/
|       +-- views.py              # /index/ (server-rendered: Projects, TestCases, Bugs)
|       +-- views2.py             # /index2/ (server-rendered: Requirements, Employees)
|       +-- api_views.py          # JWT-protected REST API for all 5 collections
|       +-- auth_views.py         # PyJWT login/refresh/register + @jwt_required decorator
|       +-- middleware.py         # Prometheus request metrics middleware
|       +-- mongo_utils.py        # MongoDB connection (reads MONGO_URI env var)
|       +-- templates/            # home.html, index.html, index2.html
|       +-- static/style.css
|
+-- graphrag/
|   +-- build_graph.py            # MongoDB -> NetworkX DiGraph -> graph.gpickle + graph.json
|   +-- chunk_graph.py            # Graph -> 1775 text chunks -> chunks.json
|   +-- retriever.py              # TF-IDF GraphRetriever + get_retriever() factory
|   +-- semantic_retriever.py     # FAISS SemanticRetriever (same interface as TF-IDF)
|   +-- embed_chunks.py           # Build chunks.faiss + id_map.json
|   +-- neo4j_retriever.py        # Neo4j 2-hop Cypher context expansion
|   +-- hybrid_retriever.py       # FAISS + Neo4j merged retrieval
|   +-- query.py                  # Interactive CLI: dry-run / Claude / Ollama
|   +-- api.py                    # FastAPI app (query, health, pipeline, metrics)
|   +-- schemas.py                # Pydantic models for FastAPI
|   +-- tasks.py                  # Celery task definitions + nightly beat schedule
|   +-- load_neo4j.py             # Load graph into Neo4j for visualization
|   +-- graph.json                # Generated: node + edge catalogue
|   +-- graph.gpickle             # Generated: NetworkX binary
|   +-- chunks.json               # Generated: 1775 text chunks
|   +-- chunks.faiss              # Generated: FAISS semantic index
|   +-- id_map.json               # Generated: FAISS int -> chunk index mapping
|
+-- frontend/                     # React SPA
|   +-- src/
|   |   +-- pages/                # Login, Dashboard, Bugs, TestCases, Projects,
|   |   |                         #   Requirements, Employees, Query
|   |   +-- components/
|   |   |   +-- ui/               # Button, Badge, Card, Input, Select, Table,
|   |   |   |                     #   Toast, Pagination, Skeleton
|   |   |   +-- charts/           # BugSeverityChart, TestCaseStatusChart (Recharts)
|   |   |   +-- layout/           # Sidebar, TopBar, Layout
|   |   +-- lib/
|   |   |   +-- api.ts            # All API calls: Django + FastAPI
|   |   |   +-- auth.ts           # JWT token storage (localStorage)
|   |   +-- types/api.ts          # TypeScript interfaces for all API responses
|   |   +-- App.tsx               # Router + protected routes
|   |   +-- main.tsx
|   +-- .env                      # VITE_DJANGO_URL, VITE_FASTAPI_URL
|   +-- package.json
|   +-- vite.config.ts
|   +-- tsconfig.json
|
+-- Uploader_Scripts/
|   +-- Base_Uploader_Scripts/    # Clear-and-insert per collection
|   +-- Comp_Uploader_Scripts/    # Compare-and-sync (tracks db_status lifecycle)
|
+-- tests/
|   +-- test_retriever.py         # GraphRetriever unit tests (11 tests)
|   +-- test_api.py               # FastAPI integration tests (11 tests)
|   +-- test_graph.py             # Artifact validation tests (10 tests)
|
+-- monitoring/
|   +-- prometheus.yml            # Scrape config for FastAPI + Django
|   +-- grafana/
|       +-- dashboards/graphrag.json         # Pre-built Grafana dashboard
|       +-- provisioning/datasources/        # Auto-provisioned Prometheus datasource
|       +-- provisioning/dashboards/         # Auto-provisioned dashboard loader
|
+-- airflow/
|   +-- dags/
|       +-- graphrag_pipeline_dag.py    # Nightly pipeline DAG (2am UTC)
|       +-- graphrag_on_demand_dag.py   # Manual trigger DAG
|
+-- .github/
|   +-- workflows/
|       +-- ci.yml                # CI: lint + tests + Docker smoke test on every push
|       +-- nightly.yml           # Nightly graph rebuild
|
+-- docs/
    +-- schema.md                 # Full field schema + graph edges + enumerations
    +-- uploader_guide.md         # Upload methods, routing, sync vs insert
    +-- graphrag_guide.md         # GraphRAG pipeline, FAISS, FastAPI, Neo4j, Cypher
    +-- api_guide.md              # REST API + JWT auth reference
    +-- ops_guide.md              # Docker, Celery, Airflow, CI/CD, monitoring, frontend
    +-- future_steps.md           # Upgrade roadmap with implementation status
```

---

## Data Model

5 node types, 10 directed edge types — 365 nodes, 1045 edges.

```
(Employee) -[:LEADS]-------------> (Project)       via lead_employee_id
(Employee) -[:ASSIGNED_TO]-------> (TestCase)      via assigned_to_employee_id
(Employee) -[:REPORTED]----------> (Bug)           via reporter_employee_id
(Employee) -[:ASSIGNED_BUG]------> (Bug)           via assignee_employee_id
(Employee) -[:RESPONSIBLE_FOR]---> (Requirement)   via verifier_employee_id
(Project)  -[:HAS_TEST_CASE]-----> (TestCase)      via project_id
(Project)  -[:HAS_BUG]-----------> (Bug)           via project_id
(Project)  -[:HAS_REQUIREMENT]---> (Requirement)   via project_id
(TestCase) -[:FOUND_BUG]---------> (Bug)           via test_case_id
(TestCase) -[:COVERS]------------> (Requirement)   via covered_by_test_case_id
```

See [`docs/schema.md`](docs/schema.md) for full field-level detail.

---

## Frontend (React SPA)

The React frontend at `http://localhost:5173` is the primary UI.

```bash
cd frontend
npm install
npm run dev      # dev server at http://localhost:5173
npm run build    # production build to frontend/dist/
```

**Pages:**
- **Login** — JWT login, tokens stored in localStorage
- **Dashboard** — summary stats, bug severity chart, test case status chart, graph health
- **Bugs** — paginated table with severity/status/domain/type filters
- **Test Cases** — paginated table with status/type/automation/team filters
- **Projects** — paginated table with domain/status/priority filters
- **Requirements** — paginated table with category/status/priority filters
- **Employees** — paginated table with department/seniority/team filters
- **Query** — GraphRAG query interface: standard, hybrid, raw chunk search; live LLM answers

**Frontend env (`frontend/.env`):**
```
VITE_DJANGO_URL=http://localhost:8000
VITE_FASTAPI_URL=http://localhost:8001
```

---

## GraphRAG Query

### Via the UI

Open the Query page in the React frontend. Select mode (standard / hybrid / chunks), enter a question, click Send.

### CLI

```bash
python graphrag/query.py                                       # interactive
python graphrag/query.py "Who leads projects with critical bugs?"  # single-shot
```

### REST API

```bash
# Standard query (dry-run, no API key needed)
curl "http://localhost:8001/query?q=critical+bugs+in+Finance"

# With JSON body + backend selection
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Which employees own the most requirements?", "top_k": 20, "backend": "auto"}'

# Hybrid: FAISS + Neo4j 2-hop context
curl -X POST http://localhost:8001/query/hybrid \
  -H "Content-Type: application/json" \
  -d '{"question": "Show path from employee to requirement via bugs"}'
```

Set `ANTHROPIC_API_KEY` in `.env` for live Claude answers.

### Retrieval modes

| Mode | Setup | Notes |
|---|---|---|
| TF-IDF (default) | None | Keyword matching, no install required |
| FAISS semantic | `python graphrag/embed_chunks.py` | Semantic similarity via all-MiniLM-L6-v2 |
| Hybrid (FAISS + Neo4j) | FAISS index + Neo4j running | Best — multi-hop graph context |

---

## Django REST API

All endpoints require `Authorization: Bearer <token>` except `/api/auth/login/`.

```bash
# Get token
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"changeme"}'

# Use token
curl http://localhost:8000/api/stats/ -H "Authorization: Bearer <token>"
curl "http://localhost:8000/api/bugs/?severity=Critical" -H "Authorization: Bearer <token>"
curl "http://localhost:8000/api/projects/?domain=Finance" -H "Authorization: Bearer <token>"
```

| Endpoint | Method | Description |
|---|---|---|
| `/api/auth/login/` | POST | Get access + refresh tokens |
| `/api/auth/refresh/` | POST | Exchange refresh token for new access token |
| `/api/auth/me/` | GET | Current user info |
| `/api/auth/register/` | POST | Create new user (admin only) |
| `/api/stats/` | GET | Collection counts + bug/test case breakdowns |
| `/api/projects/` | GET | Paginated projects with filters |
| `/api/test-cases/` | GET | Paginated test cases with filters |
| `/api/bugs/` | GET | Paginated bugs with filters |
| `/api/requirements/` | GET | Paginated requirements with filters |
| `/api/employees/` | GET | Paginated employees with filters |
| `/api/rebuild/` | POST | Trigger async graph rebuild via Celery |

See [`docs/api_guide.md`](docs/api_guide.md) for full parameter reference.

---

## Pipeline Rebuild

The graph can be rebuilt on demand or on a nightly schedule (2:00 AM UTC).

```bash
# Via REST API (queues Celery task chain)
curl -X POST http://localhost:8001/pipeline/rebuild
curl http://localhost:8001/pipeline/status/<task_id>

# Manually (step by step)
python generate_data.py
python graphrag/build_graph.py
python graphrag/chunk_graph.py
python graphrag/embed_chunks.py
python graphrag/load_neo4j.py
```

---

## Monitoring

| Tool | URL | What to look at |
|---|---|---|
| Grafana | `http://localhost:3001` | Request rate, P95 latency, chunk count, node/edge counts |
| Prometheus | `http://localhost:9090` | Raw metrics, query builder |
| FastAPI metrics | `http://localhost:8001/metrics` | Live Prometheus scrape endpoint |
| Django metrics | `http://localhost:8000/metrics` | Live Prometheus scrape endpoint |

---

## Running Tests

```bash
python -m pytest tests/ -v
# 32 tests: retriever (11), API (11), graph artifacts (10)
```

---

## Environment Variables

Copy `.env.example` to `.env`.

| Variable | Default | Description |
|---|---|---|
| `MONGO_URI` | `mongodb://localhost:27017/` | MongoDB connection string |
| `DB_NAME` | `test_db` | MongoDB database name |
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j Bolt URI |
| `NEO4J_PASSWORD` | `password` | Neo4j password |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection for Celery |
| `DJANGO_SECRET_KEY` | (insecure default) | Must be changed in production |
| `JWT_SECRET_KEY` | (insecure default) | Must be changed in production |
| `ANTHROPIC_API_KEY` | (empty) | Set for live Claude answers |
| `FASTAPI_URL` | `http://localhost:8001` | FastAPI base URL (used by Django /api/rebuild/) |
| `DEBUG` | `True` | Set to `False` in production |
| `ALLOWED_HOSTS` | `localhost 127.0.0.1` | Space-separated list |

---

## Documentation

| File | Description |
|---|---|
| [`docs/schema.md`](docs/schema.md) | Full field schema for all collections + graph edges + enumerations |
| [`docs/uploader_guide.md`](docs/uploader_guide.md) | Data ingestion: direct insert, GUI, CLI, sync vs insert |
| [`docs/graphrag_guide.md`](docs/graphrag_guide.md) | GraphRAG pipeline, FAISS, hybrid retrieval, Cypher reference |
| [`docs/api_guide.md`](docs/api_guide.md) | FastAPI + Django REST API + JWT auth reference |
| [`docs/ops_guide.md`](docs/ops_guide.md) | Docker, Celery, Airflow, CI/CD, monitoring, frontend |
| [`docs/future_steps.md`](docs/future_steps.md) | Implementation status + remaining upgrade path |
