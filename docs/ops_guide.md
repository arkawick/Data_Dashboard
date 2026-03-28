# Operations Guide

Covers Docker Compose, the React frontend, Celery, Airflow, CI/CD (GitHub Actions + Jenkins),
and monitoring (Prometheus + Grafana).

---

## Docker Compose

All services are defined in `docker-compose.yml` at the project root.

### Services

| Service | Image | Port(s) | Purpose |
|---|---|---|---|
| `mongo` | mongo:7 | 27017 | MongoDB data store |
| `neo4j` | neo4j:5 | 7474, 7687 | Graph visualization + hybrid query |
| `redis` | redis:7-alpine | 6379 | Celery broker + result backend |
| `django` | local build | 8000 | Django dashboard + REST API |
| `fastapi` | local build | 8001 | GraphRAG query API |
| `celery_worker` | local build | — | Async task execution |
| `celery_beat` | local build | — | Scheduled task trigger (nightly rebuild) |
| `prometheus` | prom/prometheus:v2.54.1 | 9090 | Metrics scraping |
| `grafana` | grafana/grafana:11.3.0 | 3001 | Metrics dashboards |
| `airflow-init` | apache/airflow:2.10 | — | One-time DB migration + user creation |
| `airflow-webserver` | apache/airflow:2.10 | 8080 | Airflow UI |
| `airflow-scheduler` | apache/airflow:2.10 | — | DAG scheduling |

### Common commands

```bash
# Start everything
docker compose up -d

# Start only infrastructure (run apps locally)
docker compose up -d mongo neo4j redis prometheus grafana

# Start specific service
docker compose up -d django

# View logs
docker compose logs -f fastapi
docker compose logs -f celery_worker --tail=100

# Rebuild image after code change
docker compose build fastapi && docker compose up -d fastapi

# Stop everything
docker compose down

# Stop and delete all volumes (full reset)
docker compose down -v
```

### Environment variables

All services read from `.env` in the project root (copy from `.env.example`).

```bash
cp .env.example .env
# Edit .env: set ANTHROPIC_API_KEY, DJANGO_SECRET_KEY, JWT_SECRET_KEY for production
```

In Docker, services connect to each other using service names as hostnames:
- `mongodb://mongo:27017/`
- `bolt://neo4j:7687`
- `redis://redis:6379/0`

For local dev (apps outside Docker), use `localhost` — the `.env.example` defaults do this.

---

## React Frontend

The frontend is a React 19 + TypeScript + Vite SPA.
It connects to Django (port 8000) for data and auth, and FastAPI (port 8001) for GraphRAG queries.

### Dev server

```bash
cd frontend
npm install
npm run dev      # starts at http://localhost:5173
```

### Production build

```bash
cd frontend
npm run build    # outputs to frontend/dist/
```

Serve `frontend/dist/` with any static file server or Nginx.

### Configuration (`frontend/.env`)

```env
VITE_DJANGO_URL=http://localhost:8000
VITE_FASTAPI_URL=http://localhost:8001
```

Change these values when deploying to a different host.

### CORS

`Django_Dashboard/config/settings.py` allows requests from:

```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",   # Vite dev server
    "http://localhost:8000",
    "http://localhost:8001",
    "http://localhost:8002",
]
```

Add your production domain here when deploying.

### Pages

| Page | Route | Description |
|---|---|---|
| Login | `/login` | JWT login form |
| Dashboard | `/` | Stats overview, charts, graph health |
| Bugs | `/bugs` | Filterable paginated bug table |
| Test Cases | `/test-cases` | Filterable paginated test case table |
| Projects | `/projects` | Filterable paginated project table |
| Requirements | `/requirements` | Filterable paginated requirements table |
| Employees | `/employees` | Filterable paginated employee table |
| Query | `/query` | GraphRAG query: standard, hybrid, raw chunk search |

### Tech stack

| Library | Version | Purpose |
|---|---|---|
| React | 19 | UI framework |
| TypeScript | 5.9 | Type safety |
| Vite | 8 | Build tool + dev server |
| React Router | 6 | Client-side routing |
| TanStack Query | 5 | Server state, caching, background refetch |
| Recharts | 3 | Charts (bug severity, test case status) |
| Radix UI | latest | Accessible headless components |
| Tailwind CSS | 3 | Utility-first styling |
| Lucide React | latest | Icons |

---

## Celery

Celery runs the asynchronous graph rebuild pipeline.

### Tasks

| Task | What it does |
|---|---|
| `task_build_graph` | MongoDB -> NetworkX -> graph.gpickle + graph.json |
| `task_chunk_graph` | graph.gpickle -> chunks.json |
| `task_embed_chunks` | chunks.json -> chunks.faiss (skipped if no sentence-transformers) |
| `task_load_neo4j` | graph.gpickle -> Neo4j |
| `task_full_pipeline` | All 4 tasks in sequence (used by beat schedule) |

### Starting workers

```bash
# Linux/Mac
celery -A graphrag.tasks worker --loglevel=info

# Windows (requires --pool=solo)
celery -A graphrag.tasks worker --loglevel=info --pool=solo

# With concurrency
celery -A graphrag.tasks worker --loglevel=info --concurrency=2
```

### Starting the beat scheduler

```bash
celery -A graphrag.tasks beat --loglevel=info
```

Configured schedule: nightly at **2:00 AM UTC**, runs `task_full_pipeline`.

To change the schedule, edit `beat_schedule` in `graphrag/tasks.py`:

```python
celery_app.conf.beat_schedule = {
    "nightly-graph-rebuild": {
        "task": "graphrag.tasks.task_full_pipeline",
        "schedule": crontab(hour=2, minute=0),
    },
}
```

### Triggering manually

```python
from graphrag.tasks import rebuild_pipeline, task_build_graph

# Full pipeline chain
result = rebuild_pipeline()
print(result.id)   # task ID for polling

# Single task
task_build_graph.delay()
```

Or via the API:

```bash
curl -X POST http://localhost:8001/pipeline/rebuild
curl http://localhost:8001/pipeline/status/<task_id>
```

### Monitoring Celery

```bash
pip install flower
celery -A graphrag.tasks flower --port=5555
# Open http://localhost:5555
```

---

## Airflow

Airflow provides visual pipeline scheduling with task-level history and retry tracking.

Open `http://localhost:8080` — login: `admin / admin`.

### DAGs

| DAG | Schedule | Purpose |
|---|---|---|
| `graphrag_nightly_pipeline` | `0 2 * * *` (2am UTC daily) | Full pipeline: seed -> build -> chunk -> embed -> neo4j |
| `graphrag_on_demand` | None (manual only) | Same pipeline, triggered on demand |

### Starting Airflow

```bash
# Via Docker Compose (recommended)
docker compose up -d airflow-init airflow-webserver airflow-scheduler
# Wait ~30 seconds for init, then open http://localhost:8080
```

### Triggering a DAG manually

**UI:** DAGs -> `graphrag_on_demand` -> Trigger DAG (play button)

**REST API:**
```bash
curl -X POST http://localhost:8080/api/v1/dags/graphrag_on_demand/dagRuns \
  -H "Content-Type: application/json" \
  -u admin:admin \
  -d '{"conf": {"reason": "manual rebuild"}}'
```

### DAG files

Edit `airflow/dags/graphrag_pipeline_dag.py` to:
- Change the schedule (`schedule="0 2 * * *"`)
- Add/remove pipeline steps
- Change retry counts (`retries: 2`)

---

## GitHub Actions CI/CD

Workflows in `.github/workflows/`:

### `ci.yml` — runs on every push and pull request to `main`

| Job | What it does |
|---|---|
| `lint` | `ruff check` on all Python files |
| `test` | `pytest tests/` with MongoDB service container |
| `docker-build` | `docker compose build`, start services, smoke test both endpoints |

### `nightly.yml` — runs at 2:00 AM UTC or on manual dispatch

Steps: seed MongoDB -> build graph -> chunk graph -> validate chunk count -> embed (optional).

### Enabling in your repo

Push to GitHub — workflows run automatically on the next push to `main`.

---

## Jenkins

`Jenkinsfile` at the project root defines a declarative pipeline for self-hosted Jenkins.

### Stages

| Stage | Branch gate | What it does |
|---|---|---|
| Checkout | all | `git checkout` |
| Install | all | `pip install` test dependencies |
| Lint | all | `ruff check` |
| Test | all | `pytest tests/` with JUnit output |
| Refresh Data | `main` only | `python generate_data.py` |
| Build Graph | `main` only | `build_graph.py` + `chunk_graph.py` |
| Embed Chunks | `main` only | `embed_chunks.py` (skips if no sentence-transformers) |
| Load Neo4j | `main` + `NEO4J_AVAILABLE=true` | `load_neo4j.py` |
| Docker Build | `main` only | `docker compose build` |
| Docker Deploy | `main` only | `docker compose up -d` |
| Smoke Test | `main` only | `curl` both Django and FastAPI |
| Validate Graph | `main` only | Assert node/edge counts >= expected |

### Running Jenkins

```bash
docker run -p 8080:8080 -v jenkins_home:/var/jenkins_home jenkins/jenkins:lts
# Open http://localhost:8080, install suggested plugins,
# create a Pipeline job pointing to this repo
```

### NEO4J_AVAILABLE gate

By default Neo4j loading is skipped in Jenkins. To enable:

Jenkins -> Manage Jenkins -> Configure System -> Environment Variables -> Add: `NEO4J_AVAILABLE = true`

---

## Prometheus + Grafana

### What's scraped

| Target | Endpoint | Metrics |
|---|---|---|
| FastAPI | `fastapi:8001/metrics` | Request count, latency, chunks loaded, node/edge counts |
| Django | `django:8000/metrics` | Request count, latency by view |

Scrape interval: 15 seconds (10s for app targets). Config: `monitoring/prometheus.yml`.

### Grafana dashboard

Auto-provisioned from `monitoring/grafana/dashboards/graphrag.json`.

**Access:** `http://localhost:3001` — login `admin / admin` -> Dashboards -> GraphRAG Dashboard.

**Panels:**
- Chunks loaded (stat)
- Graph nodes (stat)
- Graph edges (stat)
- FastAPI request rate by backend (time series)
- FastAPI P95 latency (time series)
- Django request rate (time series)
- Django P95 latency (time series)

### Adding custom metrics

In FastAPI (`graphrag/api.py`):
```python
from prometheus_client import Counter
MY_COUNTER = Counter("my_metric_total", "Description", ["label"])
MY_COUNTER.labels(label="value").inc()
```

In Django (`dashboard/middleware.py` or any view):
```python
from prometheus_client import Histogram
MY_HIST = Histogram("my_latency_seconds", "Description")
with MY_HIST.time():
    do_something()
```

---

## Production hardening checklist

Before exposing this to the internet:

- [ ] Set `DJANGO_SECRET_KEY` to a random 50-char string in `.env`
- [ ] Set `JWT_SECRET_KEY` to a random 50-char string in `.env`
- [ ] Set `NEO4J_PASSWORD` to something other than `password`
- [ ] Set `DEBUG=False` in `.env`
- [ ] Set `ALLOWED_HOSTS=yourdomain.com` in `.env`
- [ ] Add your production domain to `CORS_ALLOWED_ORIGINS` in `settings.py`
- [ ] Add Nginx in front of Django (SSL termination, static files, rate limiting)
- [ ] Set `VITE_DJANGO_URL` and `VITE_FASTAPI_URL` in `frontend/.env` to production URLs
- [ ] Build the React frontend (`npm run build`) and serve `frontend/dist/` via Nginx
- [ ] Restrict Grafana admin password (not `admin`)
- [ ] Enable MongoDB auth (`--auth` flag or `security.authorization: enabled` in mongod.conf)
- [ ] Move secrets to a vault (HashiCorp Vault or AWS Secrets Manager)
- [ ] Set up log rotation for Celery worker and beat
- [ ] Configure Sentry DSN for error tracking (`pip install sentry-sdk`)
