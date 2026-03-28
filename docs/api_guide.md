# API Guide

Two APIs plus the React frontend SPA:

- **FastAPI** (`localhost:8001`) — GraphRAG query pipeline, chunk search, pipeline control
- **Django REST** (`localhost:8000/api/`) — JWT-protected CRUD access to the 5 MongoDB collections
- **React Frontend** (`localhost:5173`) — Full SPA that consumes both APIs

---

## FastAPI (`localhost:8001`)

Interactive docs: `http://localhost:8001/docs`

No authentication required.

### Endpoints

#### `GET /health`

Service health check.

```bash
curl http://localhost:8001/health
```

```json
{
  "status": "ok",
  "chunks_loaded": 1771,
  "retriever_type": "SemanticRetriever",
  "neo4j_available": true
}
```

`retriever_type` is `"SemanticRetriever"` when `chunks.faiss` exists, `"GraphRetriever"` (TF-IDF) otherwise.

---

#### `GET /graph/stats`

Node and edge counts from the last graph build.

```bash
curl http://localhost:8001/graph/stats
```

```json
{
  "nodes": 365,
  "edges": 1045,
  "node_types": {"Employee": 25, "Project": 10, "TestCase": 100, "Bug": 150, "Requirement": 80},
  "edge_types": {"LEADS": 10, "HAS_BUG": 150, "...": "..."}
}
```

---

#### `POST /query`

GraphRAG query — retrieves context chunks and calls an LLM for the answer.

```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Which employees are assigned to critical bugs?",
    "top_k": 20,
    "chunk_types": null,
    "backend": "auto"
  }'
```

**Request body:**

| Field | Type | Default | Description |
|---|---|---|---|
| `question` | string | required | The question to answer |
| `top_k` | int | 20 | Number of chunks to retrieve (1-100) |
| `chunk_types` | list or null | null | Filter: `["entity"]`, `["relationship"]`, `["neighbourhood"]`, or any combination |
| `backend` | string | `"auto"` | `auto`, `claude`, `ollama`, `dry_run` |

`backend: "auto"` selects Claude if `ANTHROPIC_API_KEY` is set, Ollama if `OLLAMA_MODEL` is set, else dry_run.

**Response:**

```json
{
  "question": "Which employees are assigned to critical bugs?",
  "backend": "dry_run",
  "chunks_retrieved": 20,
  "chunks": ["..."],
  "answer": "=== DRY-RUN MODE ..."
}
```

---

#### `GET /query`

Convenience alias for browser / curl testing.

```bash
curl "http://localhost:8001/query?q=critical+bugs&top_k=5&backend=auto"
```

---

#### `GET /chunks/search`

Raw chunk retrieval — no LLM call, returns matching chunks only.

```bash
curl "http://localhost:8001/chunks/search?q=security+requirements&top_k=10"
curl "http://localhost:8001/chunks/search?q=Finance+bugs&chunk_types=entity,relationship"
```

**Parameters:**

| Param | Type | Description |
|---|---|---|
| `q` | string | Search query |
| `top_k` | int | Number of results (default 15, max 100) |
| `chunk_types` | string | Comma-separated chunk types to filter |

---

#### `POST /query/hybrid`

Hybrid GraphRAG — combines FAISS semantic search with Neo4j 2-hop graph expansion.

```bash
curl -X POST http://localhost:8001/query/hybrid \
  -H "Content-Type: application/json" \
  -d '{"question": "Show relationships between employees and requirements via bugs"}'
```

Requires `chunks.faiss` (run `embed_chunks.py`) and Neo4j running.
Falls back to standard query if either is unavailable.

**Response** adds `graph_paths` field:

```json
{
  "question": "...",
  "backend": "dry_run",
  "chunks_retrieved": 15,
  "chunks": ["..."],
  "graph_paths": [
    {"source": "EMP-001", "relation": "LEADS", "target": "PROJ-003", "src_label": "Employee", "tgt_label": "Project"},
    "..."
  ],
  "answer": "..."
}
```

---

#### `POST /pipeline/rebuild`

Trigger the full graph rebuild pipeline asynchronously via Celery. Requires Redis running.

```bash
curl -X POST http://localhost:8001/pipeline/rebuild
```

```json
{"task_id": "abc123", "status": "queued", "message": "Pipeline queued: build_graph -> chunk -> embed -> neo4j"}
```

---

#### `GET /pipeline/status/{task_id}`

Poll the status of a queued pipeline task.

```bash
curl http://localhost:8001/pipeline/status/abc123
```

```json
{"task_id": "abc123", "status": "SUCCESS", "result": "{'neo4j': 'ok', 'embed': 'ok', ...}"}
```

Celery task states: `PENDING`, `STARTED`, `SUCCESS`, `FAILURE`, `RETRY`.

---

#### `GET /metrics`

Prometheus metrics endpoint (scraped automatically by Prometheus).

```bash
curl http://localhost:8001/metrics
```

Metrics exposed:
- `graphrag_requests_total` — counter by endpoint + backend
- `graphrag_request_seconds` — histogram by endpoint
- `graphrag_chunks_loaded` — gauge
- `graphrag_graph_nodes_total` — gauge
- `graphrag_graph_edges_total` — gauge

---

## Django REST API (`localhost:8000/api/`)

JWT authentication required on all endpoints except `/api/auth/login/`.

### Authentication

#### `POST /api/auth/login/`

Exchange credentials for JWT tokens.

```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "changeme"}'
```

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 28800,
  "username": "admin",
  "role": "admin"
}
```

Access token expires in 8 hours. Refresh token expires in 7 days.

---

#### `POST /api/auth/refresh/`

Get a new access token using a refresh token.

```bash
curl -X POST http://localhost:8000/api/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJ..."}'
```

---

#### `GET /api/auth/me/`

Return current user info.

```bash
curl http://localhost:8000/api/auth/me/ \
  -H "Authorization: Bearer <access_token>"
```

---

#### `POST /api/auth/register/`

Create a new user. Admin role required.

```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"username": "newuser", "password": "secret", "role": "viewer"}'
```

Roles: `admin`, `viewer`.

---

### First-time user setup

If no users exist yet, create the first admin from the Django shell:

```bash
cd Django_Dashboard
python manage.py shell
>>> from dashboard.auth_views import create_user
>>> create_user("admin", "changeme", role="admin")
```

---

### Data endpoints

All data endpoints accept `Authorization: Bearer <token>` and return paginated JSON.

#### Common query parameters

| Param | Description |
|---|---|
| `page` | Page number (default 1) |
| `page_size` | Results per page (default 50) |

**Response shape:**

```json
{
  "count": 150,
  "page": 1,
  "pages": 3,
  "results": ["..."]
}
```

---

#### `GET /api/stats/`

Summary counts and breakdowns for all collections.

```bash
curl http://localhost:8000/api/stats/ -H "Authorization: Bearer <token>"
```

```json
{
  "counts": {"employees": 25, "projects": 10, "test_cases": 100, "bugs": 150, "requirements": 80},
  "bug_by_severity": {"Critical": 38, "Major": 42, "Minor": 35, "Trivial": 35},
  "tc_by_status": {"Passed": 22, "Failed": 19, "Pending": 21, "Skipped": 18, "Blocked": 20}
}
```

---

#### `GET /api/projects/`

```bash
curl "http://localhost:8000/api/projects/?domain=Finance&status=Active" \
  -H "Authorization: Bearer <token>"
```

Filters: `domain`, `status`, `priority`

---

#### `GET /api/test-cases/`

```bash
curl "http://localhost:8000/api/test-cases/?status=Failed&team=Alpha" \
  -H "Authorization: Bearer <token>"
```

Filters: `domain`, `status`, `team`, `project_name`, `test_type`, `automation_status`

---

#### `GET /api/bugs/`

```bash
curl "http://localhost:8000/api/bugs/?severity=Critical&status=Open" \
  -H "Authorization: Bearer <token>"
```

Filters: `severity`, `status`, `priority`, `domain`, `team`, `bug_type`, `project_name`

---

#### `GET /api/requirements/`

```bash
curl "http://localhost:8000/api/requirements/?category=Security&status=Approved" \
  -H "Authorization: Bearer <token>"
```

Filters: `category`, `status`, `priority`, `domain`, `team`, `project_name`

---

#### `GET /api/employees/`

```bash
curl "http://localhost:8000/api/employees/?department=Engineering&seniority=Senior" \
  -H "Authorization: Bearer <token>"
```

Filters: `department`, `team`, `seniority`, `role`

---

#### `POST /api/rebuild/`

Trigger graph rebuild (proxies to FastAPI `/pipeline/rebuild`). Returns Celery task ID.

```bash
curl -X POST http://localhost:8000/api/rebuild/ \
  -H "Authorization: Bearer <token>"
```

---

#### `GET /metrics`

Django Prometheus metrics (scraped by Prometheus).

```bash
curl http://localhost:8000/metrics
```

Metrics: `django_requests_total`, `django_request_seconds`

---

## React Frontend (`localhost:5173`)

The React SPA consumes both APIs. It reads base URLs from `frontend/.env`:

```env
VITE_DJANGO_URL=http://localhost:8000
VITE_FASTAPI_URL=http://localhost:8001
```

**Token flow:**
1. User submits credentials on `/login`
2. Frontend POSTs to `${DJANGO_URL}/api/auth/login/`
3. Access + refresh tokens stored in `localStorage`
4. All subsequent Django calls include `Authorization: Bearer <access_token>`
5. On 401, frontend auto-refreshes token via `/api/auth/refresh/`, then retries
6. On refresh failure, redirects to `/login`

**FastAPI calls** (Query page) send no auth header — FastAPI is unauthenticated.

### CORS

Django's `CORS_ALLOWED_ORIGINS` in `settings.py` must include the frontend origin:

```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",   # Vite dev server
    "http://localhost:3000",   # alternative dev port
    "http://localhost:8000",
    "http://localhost:8001",
    "http://localhost:8002",
]
```

Add your production domain when deploying.
