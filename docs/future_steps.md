# Future Steps — Production Grade Upgrade Path

All items in the prioritised roadmap have been implemented as of 2026-03-28.
This document is kept for reference and to describe what remains for full cloud-scale deployment.

---

## Implementation Status

| Priority | Item | Status |
|---|---|---|
| 1 | Docker Compose — containerise all services | **Done** |
| 2 | FastAPI query endpoint | **Done** |
| 3 | Semantic embeddings + FAISS | **Done** |
| 4 | Neo4j in query pipeline (hybrid retriever) | **Done** |
| 5 | Celery + Redis — async graph rebuilds | **Done** |
| 6 | JWT auth in Django | **Done** |
| 7 | GitHub Actions CI/CD | **Done** |
| 8 | Prometheus + Grafana | **Done** |
| 9 | Jenkinsfile | **Done** |
| 10 | Airflow DAG — nightly pipeline | **Done** |
| 11 | React SPA frontend | **Done** |
| 12 | Kafka ingestion — real-time event stream | Not implemented |

---

## Current Stack

```
[Airflow / Celery Beat]          <- nightly schedule
        |
    MongoDB
        |
  build_graph.py  -->  NetworkX DiGraph  -->  graph.gpickle
        |                                -->  graph.json
  chunk_graph.py  -->  chunks.json
        |
  embed_chunks.py -->  chunks.faiss  (FAISS + all-MiniLM-L6-v2)
        |
  load_neo4j.py   -->  Neo4j (visualization + hybrid context)
        |
  FastAPI (api.py)
    /query          <-- TF-IDF or FAISS retrieval
    /query/hybrid   <-- FAISS + Neo4j 2-hop expansion
    /pipeline/rebuild  <-- triggers Celery chain
    /metrics           <-- Prometheus scrape
        |
  Django (REST + dashboard)
    /api/*          <-- JWT-protected REST API
    /index/         <-- server-rendered dashboard (legacy)
    /metrics        <-- Prometheus scrape
        |
  React SPA (Vite + TypeScript)
    localhost:5173  <-- primary UI
    /login          <-- JWT login
    /dashboard      <-- stats + charts
    /bugs           <-- filterable bug table
    /test-cases     <-- filterable test case table
    /projects       <-- filterable project table
    /requirements   <-- filterable requirements table
    /employees      <-- filterable employee table
    /query          <-- GraphRAG query interface (standard + hybrid + chunks)
        |
  Prometheus + Grafana  <-- request latency, error rates, token usage
        |
  GitHub Actions / Jenkins  <-- test + build + deploy on push
```

---

## What Remains (not yet implemented)

### Kafka ingestion

Real-time event streaming — bugs/test results written to Kafka topics, consumed into MongoDB.
Only needed if data volumes require sub-second ingestion latency.

High effort, high infrastructure overhead. Use only if:
- External systems (Jira, CI tools) need to push events in real time
- Data refresh frequency needs to be higher than the nightly Airflow schedule

Recommended approach when needed:
```
External system  ->  Kafka topic  ->  Kafka consumer  ->  MongoDB
                                   (Python consumer using confluent-kafka)
```

### Cloud deployment

The Docker Compose setup runs locally. To deploy to cloud:

| Component | Cloud option |
|---|---|
| MongoDB | MongoDB Atlas (managed) |
| Neo4j | Neo4j AuraDB (managed free tier) |
| Redis | AWS ElastiCache or Upstash |
| Django + FastAPI | AWS ECS, GCP Cloud Run, or Kubernetes |
| Celery workers | Same ECS/K8s cluster |
| Airflow | AWS MWAA or Astronomer |
| Monitoring | Grafana Cloud (free tier) |
| React frontend | Vercel, Netlify, or S3 + CloudFront |

### Nginx (for production HTTP)

Add Nginx as a reverse proxy in front of Django and to serve the React build:
- SSL/TLS termination
- Static file serving (`/static/` and React `dist/`)
- Rate limiting

```yaml
# Add to docker-compose.yml
nginx:
  image: nginx:alpine
  ports: ["80:80", "443:443"]
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf
    - ./Django_Dashboard/staticfiles:/static
    - ./frontend/dist:/usr/share/nginx/html
  depends_on: [django, fastapi]
```

### Vector store upgrade (optional)

The current FAISS index uses `all-MiniLM-L6-v2` (384 dimensions, fast, general-purpose).
For higher retrieval quality on technical text:

| Option | Model | Notes |
|---|---|---|
| Voyage AI | `voyage-3` | Best for technical/code content, API-based |
| OpenAI | `text-embedding-3-small` | Good balance of quality and cost |
| Local | `bge-large-en-v1.5` | Best open-source, requires more RAM |

To upgrade: change `MODEL_NAME` in `graphrag/embed_chunks.py` and re-run it.

### LangSmith / Arize tracing

LLM observability — trace every retrieval, prompt, and LLM response.

```bash
pip install langsmith
export LANGCHAIN_API_KEY=ls__...
export LANGCHAIN_TRACING_V2=true
```

Works without changing application code when using LangChain. For direct Anthropic calls,
wrap `ask_claude()` in `graphrag/query.py` with a LangSmith trace decorator.

### Sentry error tracking

```bash
pip install sentry-sdk
```

In `Django_Dashboard/config/settings.py`:
```python
import sentry_sdk
sentry_sdk.init(dsn=os.environ.get("SENTRY_DSN", ""), traces_sample_rate=1.0)
```

In `graphrag/api.py`:
```python
import sentry_sdk
sentry_sdk.init(dsn=os.environ.get("SENTRY_DSN", ""))
```

---

## Layer Reference

### Layer 1 — Data Ingestion

| Tool | Status | Purpose |
|---|---|---|
| Direct insert (`generate_data.py`) | Done | Dev reset + quick seed |
| Excel uploader | Done | Manual data entry |
| Airflow DAG | Done | Nightly scheduled pipeline |
| Celery tasks | Done | On-demand async pipeline |
| Apache Kafka | Not implemented | Real-time event streaming |
| dbt | Not implemented | Data transformation layer |
| Great Expectations | Not implemented | Data quality validation |

### Layer 2 — Graph & Retrieval

| Tool | Status | Purpose |
|---|---|---|
| NetworkX (graph.gpickle) | Done | In-memory graph snapshot |
| TF-IDF retriever | Done | Keyword-based chunk retrieval |
| FAISS + sentence-transformers | Done | Semantic chunk retrieval |
| Neo4j (visualization) | Done | Visual graph browser |
| Neo4j (query pipeline) | Done | 2-hop Cypher context expansion |
| Hybrid retriever | Done | FAISS + Neo4j merged |
| LlamaIndex Knowledge Graph | Not implemented | Higher-level GraphRAG framework |

### Layer 3 — LLM & API

| Tool | Status | Purpose |
|---|---|---|
| FastAPI | Done | REST API for all query modes |
| Claude backend | Done | Live LLM answers via API |
| Ollama backend | Done | Local LLM answers |
| Dry-run mode | Done | No API key needed |
| Redis (result cache) | Done (broker only) | Cache not yet implemented |
| LangChain/LlamaIndex | Not implemented | Chain management + agents |
| LangSmith | Not implemented | LLM observability |

### Layer 4 — Web Application

| Tool | Status | Purpose |
|---|---|---|
| Django dashboard (server-rendered) | Done | Legacy HTML views |
| JWT authentication | Done | Token-based auth |
| REST API | Done | Paginated JSON endpoints |
| Prometheus middleware | Done | Request metrics |
| CORS | Done | Cross-origin support for React |
| Celery + Redis | Done | Async task queue |
| React SPA (Vite + TypeScript) | Done | Primary frontend |
| TanStack Query | Done | Data fetching + caching |
| Recharts | Done | Interactive charts |
| Django Channels | Not implemented | WebSocket streaming |

### Layer 5 — Infrastructure

| Tool | Status | Purpose |
|---|---|---|
| Docker Compose | Done | Local containerised deployment |
| Nginx | Not implemented | Reverse proxy + SSL |
| GitHub Actions | Done | CI/CD on push |
| Jenkins | Done | Self-hosted CI/CD |
| Kubernetes | Not implemented | Cloud orchestration + autoscaling |
| Vault / Secrets Manager | Not implemented | Production secrets management |

### Layer 6 — Observability

| Tool | Status | Purpose |
|---|---|---|
| Prometheus | Done | Metrics collection |
| Grafana | Done | Metrics dashboards |
| Sentry | Not implemented | Error tracking |
| LangSmith / Arize | Not implemented | LLM trace observability |
| Loki / ELK | Not implemented | Log aggregation |
| OpenTelemetry | Not implemented | Distributed tracing |
