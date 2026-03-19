# Future Steps — Production Grade Upgrade Path

This document outlines what to add to the current stack to move from a local prototype
to a production-grade GraphRAG system.

---

## Current Stack

```
MongoDB  ->  NetworkX  ->  TF-IDF  ->  Django  ->  Neo4j
                                    ->  query.py (Claude / Ollama)
```

---

## Layer 1 — Data Ingestion & Pipeline

**Problem:** Data only enters via Excel upload or `generate_data.py`. Production needs
scheduled, validated, reliable ingestion.

| Tool | Purpose |
|---|---|
| **Apache Airflow** | Schedule pipelines — nightly MongoDB refresh, graph rebuild, re-chunking |
| **Apache Kafka** | Real-time event streaming — bugs/test results written to Kafka, consumed into MongoDB |
| **dbt** | Data transformation layer — clean, validate, and model raw MongoDB data before graph build |
| **Great Expectations** | Data quality checks — validate FK integrity, enum values, null rates before insert |

---

## Layer 2 — Graph & Retrieval

**Problem:** TF-IDF is keyword-only and misses semantic similarity ("critical defect" won't
match "Critical bug"). Neo4j is running but not integrated into the query pipeline.

| Tool | Purpose |
|---|---|
| **Neo4j as primary graph store** | Replace `graph.gpickle` — live Cypher queries instead of a pickled snapshot |
| **Sentence Transformers / Voyage AI** | Replace TF-IDF with vector embeddings for semantic retrieval |
| **FAISS or Chroma** | Vector index over chunk embeddings — sub-millisecond ANN search |
| **LlamaIndex Knowledge Graph Index** | Higher-level GraphRAG framework wrapping Neo4j + vector store together |

**Upgraded retrieval pipeline:**
```
Question -> embed -> FAISS ANN search  -> top-K chunks  \
         -> Cypher on Neo4j            -> graph context  --> merge -> LLM
```

---

## Layer 3 — LLM & API Layer

**Problem:** `query.py` is a CLI script. Production needs a proper API, streaming responses,
session memory, and cost control.

| Tool | Purpose |
|---|---|
| **FastAPI** | REST + WebSocket API for the query interface (replaces CLI script) |
| **LangChain or LlamaIndex** | Chain management, conversation memory, tool use, ReAct agents over the graph |
| **LangSmith / Arize Phoenix** | LLM observability — trace every retrieval, prompt, and LLM response |
| **Redis** | Cache frequent query results, store conversation history per session |
| **Token budget / rate limiting** | Control API spend per user or session |

---

## Layer 4 — Web Application

**Problem:** Django dashboard has no auth, no REST API, no async, and is a read-only viewer.

| Tool | Purpose |
|---|---|
| **Django REST Framework (DRF)** | Proper REST API with serializers, viewsets, and pagination |
| **Django Channels + WebSockets** | Stream LLM responses to the browser in real time |
| **JWT / OAuth2 (django-allauth)** | Authentication and role-based access control |
| **Celery + Redis** | Async task queue — run graph rebuilds and chunk regeneration in background |
| **React or Next.js** (optional) | Replace server-rendered templates with a proper SPA frontend |

---

## Layer 5 — Infrastructure & Deployment

**Problem:** Everything runs on localhost with no isolation, no scaling, and no fault tolerance.

| Tool | Purpose |
|---|---|
| **Docker + Docker Compose** | Containerise all services — MongoDB, Neo4j, Redis, Django, FastAPI |
| **Nginx** | Reverse proxy, SSL termination, static file serving |
| **Kubernetes (K8s)** | Orchestration, auto-scaling, rolling deploys (when cloud scale is needed) |
| **GitHub Actions** | CI/CD — run tests, build Docker images, deploy on push |
| **HashiCorp Vault / AWS Secrets Manager** | Secrets management — no hardcoded credentials in code |

---

## Layer 6 — Observability

**Problem:** Currently zero visibility into system health, query latency, or errors.

| Tool | Purpose |
|---|---|
| **Prometheus + Grafana** | Metrics — query latency, retrieval times, LLM token usage, error rates |
| **Loki** | Log aggregation (lightweight alternative to ELK stack) |
| **Sentry** | Error tracking and alerting for Django and FastAPI |
| **OpenTelemetry** | Distributed tracing across MongoDB, Neo4j, Redis, and LLM calls |

---

## Target Architecture

```
                     [Airflow / Kafka]
                            |
                        MongoDB
                            |
                  build_graph.py (scheduled)
                    /              \
              Neo4j             chunk_graph.py
                |                      |
         Cypher queries          Embeddings (Voyage AI)
                 \                    /
                  FAISS / Chroma index
                            |
                       FastAPI (query API)
                      /      |      \
                LangChain  Redis   LangSmith
                            |
                       Django + DRF
                      (dashboard + auth)
                            |
                          Nginx
                            |
                    React / Next.js frontend
                            |
                Prometheus / Grafana / Sentry
```

---

## Prioritised Roadmap

Work through these roughly in order — each step is independently useful.

| Priority | Add | Effort | Impact |
|---|---|---|---|
| 1 | **Docker Compose** — containerise all services | Low | Reproducible, shareable environment |
| 2 | **FastAPI query endpoint** — expose GraphRAG as an API | Low | Makes the system callable from anything |
| 3 | **Semantic embeddings + FAISS** — replace TF-IDF | Medium | Much better retrieval quality |
| 4 | **Neo4j in query pipeline** — live Cypher for multi-hop context | Medium | Graph-aware, multi-hop LLM answers |
| 5 | **Celery + Redis** — async graph rebuilds | Medium | Non-blocking data refresh |
| 6 | **JWT auth in Django** — multi-user access control | Medium | Secure, role-based dashboard |
| 7 | **LangSmith tracing** — LLM observability | Low | Full visibility into retrieval and prompts |
| 8 | **Airflow DAG** — nightly graph rebuild pipeline | High | Automated data freshness |
| 9 | **Prometheus + Grafana** — system health monitoring | Medium | Latency, error rate, token usage dashboards |
| 10 | **Jenkins** — CI/CD pipeline for code and deployments | Medium | Automated test, build, deploy on every git push |
| 11 | **n8n** — event-driven workflow automation | Low | Trigger pipelines from Jira, Slack, S3, file uploads |
| 12 | **Kafka ingestion** — real-time event stream | High | Live bug/test result ingestion (only if needed) |

---

## Layer 7 — Automation & CI/CD: n8n and Jenkins

Both tools are applicable to this project but serve different roles. They are complementary,
not competing — you would typically use both.

---

### n8n — Workflow Automation (Data & Event Triggers)

**What it is:** A self-hosted, low-code workflow automation tool (like Zapier but open source).
It connects services via a visual node editor and can react to events, webhooks, schedules,
and file system changes.

**How it fits this project:**

| Use case | n8n workflow |
|---|---|
| Excel file dropped in a folder or S3 bucket | Trigger -> run uploader script -> notify Slack |
| Jira/GitHub issue created | Webhook -> insert bug into MongoDB -> trigger graph rebuild |
| Nightly data refresh | Schedule -> `generate_data.py` -> `build_graph.py` -> `chunk_graph.py` -> `load_neo4j.py` |
| Graph rebuild completes | Trigger -> send email/Slack summary with node/edge counts |
| Django API query logged | Webhook -> log to external analytics tool |
| New Excel uploaded via dashboard | HTTP trigger -> run uploader -> confirm in UI |

**Example n8n pipeline for nightly graph rebuild:**
```
[Cron: 2am] -> [SSH/Execute: python generate_data.py]
            -> [SSH/Execute: python graphrag/build_graph.py]
            -> [SSH/Execute: python graphrag/chunk_graph.py]
            -> [SSH/Execute: python graphrag/load_neo4j.py]
            -> [Slack: "Graph rebuilt: 365 nodes, 1045 edges"]
```

**Setup:**
```bash
# Docker
docker run -p 5678:5678 -v ~/.n8n:/home/node/.n8n n8nio/n8n

# Open http://localhost:5678
```

**Best for:** Non-engineers triggering pipelines, event-driven ingestion, integrating with
external tools (Jira, GitHub, Slack, SharePoint, S3) without writing glue code.

---

### Jenkins — CI/CD (Code, Build, Deploy)

**What it is:** A self-hosted CI/CD automation server. Runs pipelines defined as code
(Jenkinsfile) triggered by git events or on a schedule.

**How it fits this project:**

| Use case | Jenkins pipeline stage |
|---|---|
| Code pushed to main branch | Run tests -> build Docker images -> deploy Django + FastAPI |
| `generate_data.py` changed | Run data integrity checks, verify FK relationships |
| `graphrag/` scripts changed | Rebuild graph, re-chunk, validate chunk count matches expected |
| Pull request opened | Run linting (flake8/ruff) + unit tests |
| Nightly | Full pipeline: data refresh -> graph build -> chunk -> Neo4j reload |
| Docker image built | Push to registry (Docker Hub / ECR / GCR) |

**Example Jenkinsfile:**
```groovy
pipeline {
    agent any

    triggers {
        cron('H 2 * * *')   // nightly at 2am
    }

    stages {
        stage('Checkout') {
            steps { git 'https://github.com/yourorg/data-dashboard' }
        }

        stage('Test') {
            steps { sh 'python -m pytest tests/' }
        }

        stage('Refresh Data') {
            steps { sh 'python generate_data.py' }
        }

        stage('Build Graph') {
            steps {
                sh 'python graphrag/build_graph.py'
                sh 'python graphrag/chunk_graph.py'
            }
        }

        stage('Load Neo4j') {
            steps { sh 'python graphrag/load_neo4j.py' }
        }

        stage('Deploy') {
            steps { sh 'docker compose up -d --build' }
        }
    }

    post {
        success { slackSend message: "Pipeline passed. Graph rebuilt successfully." }
        failure { slackSend message: "Pipeline FAILED. Check Jenkins logs." }
    }
}
```

**Setup:**
```bash
# Docker
docker run -p 8080:8080 -v jenkins_home:/var/jenkins_home jenkins/jenkins:lts

# Open http://localhost:8080
```

**Best for:** Engineers managing code deployments, running tests on every commit,
building and pushing Docker images, enforcing quality gates before deploy.

---

### n8n vs Jenkins — When to Use Which

| Scenario | Use |
|---|---|
| Trigger pipeline from a Slack message or form | n8n |
| Trigger pipeline on git push / PR merge | Jenkins |
| Connect to Jira, SharePoint, S3, or Slack | n8n |
| Build and push Docker images | Jenkins |
| Non-technical user needs to run a data refresh | n8n (UI-based trigger) |
| Enforce test passing before deploy | Jenkins |
| Event-driven ingestion (webhook from external system) | n8n |
| Nightly scheduled full pipeline with stages | Either (Jenkins more robust) |
| Low infrastructure overhead | n8n (simpler setup) |

**Recommended setup for this project:**
- **n8n** handles event-driven data ingestion — external triggers, Excel uploads, Jira webhooks
- **Jenkins** handles code CI/CD — test, build Docker, deploy on git push

---

## Quick Wins (Start Here)

These three alone move the project from a local prototype to something deployable:

### 1. Docker Compose

```yaml
# docker-compose.yml (outline)
services:
  mongo:
    image: mongo:7
    ports: ["27017:27017"]

  neo4j:
    image: neo4j:5
    ports: ["7474:7474", "7687:7687"]
    environment:
      NEO4J_AUTH: neo4j/password

  redis:
    image: redis:7
    ports: ["6379:6379"]

  django:
    build: ./Django_Dashboard
    ports: ["8000:8000"]
    depends_on: [mongo, redis]

  fastapi:
    build: ./graphrag
    ports: ["8001:8001"]
    depends_on: [mongo, neo4j, redis]
```

### 2. FastAPI query endpoint

```python
# graphrag/api.py
from fastapi import FastAPI
from graphrag.retriever import GraphRetriever

app = FastAPI()
retriever = GraphRetriever()

@app.get("/query")
def query(q: str, top_k: int = 20):
    chunks = retriever.retrieve(q, top_k=top_k)
    context = "\n\n".join(f"[{i+1}] {c['text']}" for i, c in enumerate(chunks))
    return {"question": q, "chunks": chunks, "context": context}
```

Run with: `uvicorn graphrag.api:app --port 8001`

### 3. FAISS semantic index (replaces TF-IDF)

```bash
pip install faiss-cpu sentence-transformers
```

```python
from sentence_transformers import SentenceTransformer
import faiss, json, numpy as np

model = SentenceTransformer("all-MiniLM-L6-v2")
chunks = json.load(open("graphrag/chunks.json"))
texts = [c["text"] for c in chunks]

embeddings = model.encode(texts, show_progress_bar=True)
embeddings = np.array(embeddings).astype("float32")

index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(embeddings)
faiss.write_index(index, "graphrag/chunks.faiss")

# Query
def semantic_retrieve(question, top_k=20):
    q_emb = model.encode([question]).astype("float32")
    _, indices = index.search(q_emb, top_k)
    return [chunks[i] for i in indices[0]]
```
