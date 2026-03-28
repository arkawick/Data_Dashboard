"""
graphrag/api.py
===============
FastAPI query endpoint for the GraphRAG pipeline.

Endpoints:
  GET  /health                  - service health + chunk count
  GET  /graph/stats             - node/edge statistics
  POST /query                   - GraphRAG query (returns LLM answer)
  GET  /query?q=...             - convenience alias for browser testing
  GET  /chunks/search?q=...     - raw chunk retrieval (no LLM)
  POST /query/hybrid            - FAISS + Neo4j hybrid retrieval
  POST /pipeline/rebuild        - trigger async graph rebuild via Celery
  GET  /pipeline/status/{id}    - check Celery task status
  GET  /metrics                 - Prometheus metrics

Run locally:
    uvicorn graphrag.api:app --reload --port 8001
"""

import json
import os
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, Gauge, make_asgi_app

from graphrag.schemas import (
    QueryRequest, QueryResponse, HybridQueryResponse,
    HealthResponse, GraphStatsResponse, RebuildResponse, TaskStatusResponse,
)

# ── Prometheus metrics ────────────────────────────────────────────────────────

REQUEST_COUNT = Counter(
    "graphrag_requests_total",
    "Total GraphRAG API requests",
    ["endpoint", "backend"],
)
REQUEST_LATENCY = Histogram(
    "graphrag_request_seconds",
    "Request latency in seconds",
    ["endpoint"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0],
)
CHUNKS_LOADED = Gauge("graphrag_chunks_loaded", "Number of chunks loaded in retriever")
GRAPH_NODES = Gauge("graphrag_graph_nodes_total", "Total nodes in graph")
GRAPH_EDGES = Gauge("graphrag_graph_edges_total", "Total edges in graph")

# ── App state ─────────────────────────────────────────────────────────────────

_state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load retriever and graph stats once at startup."""
    from graphrag.retriever import get_retriever
    _state["retriever"] = get_retriever()
    _state["retriever_type"] = type(_state["retriever"]).__name__

    # Load graph stats from graph.json
    graph_json = os.path.join(os.path.dirname(__file__), "graph.json")
    if os.path.exists(graph_json):
        with open(graph_json, encoding="utf-8") as f:
            data = json.load(f)
        stats = data.get("stats", {})
        _state["graph_stats"] = stats
        GRAPH_NODES.set(stats.get("nodes", 0))
        GRAPH_EDGES.set(stats.get("edges", 0))
    else:
        _state["graph_stats"] = {}

    CHUNKS_LOADED.set(len(_state["retriever"].chunks))
    print(f"[API] Retriever: {_state['retriever_type']}, "
          f"Chunks: {len(_state['retriever'].chunks)}")
    yield
    _state.clear()


app = FastAPI(
    title="GraphRAG Query API",
    description="REST API for the Data Dashboard GraphRAG pipeline",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://django:8000",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ── Prometheus metrics endpoint ───────────────────────────────────────────────

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


# ── Middleware ────────────────────────────────────────────────────────────────

@app.middleware("http")
async def metrics_middleware(request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start
    path = request.url.path
    if path != "/metrics":
        REQUEST_LATENCY.labels(endpoint=path).observe(elapsed)
    return response


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["system"])
def health():
    """Service health check."""
    neo4j_ok = _check_neo4j()
    return HealthResponse(
        status="ok",
        chunks_loaded=len(_state["retriever"].chunks),
        retriever_type=_state["retriever_type"],
        neo4j_available=neo4j_ok,
    )


def _check_neo4j() -> bool:
    try:
        from graphrag.neo4j_retriever import Neo4jRetriever
        uri  = os.environ.get("NEO4J_URI",      "bolt://localhost:7687")
        user = os.environ.get("NEO4J_USER",     "neo4j")
        pwd  = os.environ.get("NEO4J_PASSWORD", "password")
        with Neo4jRetriever(uri, user, pwd) as r:
            return r.ping()
    except Exception:
        return False


# ── Graph stats ───────────────────────────────────────────────────────────────

@app.get("/graph/stats", response_model=GraphStatsResponse, tags=["graph"])
def graph_stats():
    """Return node and edge counts from the last graph build."""
    stats = _state.get("graph_stats", {})
    return GraphStatsResponse(
        nodes=stats.get("nodes", 0),
        edges=stats.get("edges", 0),
        node_types=stats.get("node_types", {}),
        edge_types=stats.get("edge_types", {}),
    )


# ── Chunk search (no LLM) ─────────────────────────────────────────────────────

@app.get("/chunks/search", tags=["retrieval"])
def chunk_search(
    q: str = Query(..., min_length=1),
    top_k: int = Query(15, ge=1, le=100),
    chunk_types: Optional[str] = Query(None, description="Comma-separated types"),
):
    """Retrieve chunks matching a query without calling any LLM."""
    types = chunk_types.split(",") if chunk_types else None
    chunks = _state["retriever"].retrieve(q, top_k=top_k, chunk_types=types)
    REQUEST_COUNT.labels(endpoint="/chunks/search", backend="none").inc()
    return {"query": q, "chunks_retrieved": len(chunks), "chunks": chunks}


# ── Main query endpoint ───────────────────────────────────────────────────────

@app.post("/query", response_model=QueryResponse, tags=["query"])
def query_post(req: QueryRequest):
    """GraphRAG query — retrieves context chunks and calls an LLM for the answer."""
    return _run_query(req.question, req.top_k, req.chunk_types, req.backend)


@app.get("/query", response_model=QueryResponse, tags=["query"])
def query_get(
    q: str = Query(..., min_length=1),
    top_k: int = Query(20, ge=1, le=100),
    backend: str = Query("auto"),
):
    """GraphRAG query via GET for browser / quick testing."""
    return _run_query(q, top_k, None, backend)


def _run_query(question: str, top_k: int, chunk_types, backend_override: str):
    from graphrag.query import detect_backend, ask_claude, ask_ollama, dry_run

    retriever = _state["retriever"]
    chunks = retriever.retrieve(question, top_k=top_k, chunk_types=chunk_types)
    context = "\n\n".join(
        f"[{i+1}] ({c['type']}) {c['text']}" for i, c in enumerate(chunks)
    )

    backend = backend_override if backend_override != "auto" else detect_backend()

    try:
        if backend == "claude":
            answer = ask_claude(question, context)
        elif backend == "ollama":
            answer = ask_ollama(question, context)
        else:
            backend = "dry_run"
            answer = dry_run(question, context, chunks)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM backend error: {exc}")

    REQUEST_COUNT.labels(endpoint="/query", backend=backend).inc()
    return QueryResponse(
        question=question,
        backend=backend,
        chunks_retrieved=len(chunks),
        chunks=chunks,
        answer=answer,
    )


# ── Hybrid query (FAISS + Neo4j) ──────────────────────────────────────────────

@app.post("/query/hybrid", response_model=HybridQueryResponse, tags=["query"])
def query_hybrid(req: QueryRequest):
    """Hybrid GraphRAG query combining FAISS semantic search + Neo4j graph context."""
    try:
        from graphrag.hybrid_retriever import HybridRetriever
        from graphrag.query import detect_backend, ask_claude, ask_ollama, dry_run

        uri  = os.environ.get("NEO4J_URI",      "bolt://localhost:7687")
        user = os.environ.get("NEO4J_USER",     "neo4j")
        pwd  = os.environ.get("NEO4J_PASSWORD", "password")

        hr = HybridRetriever(neo4j_uri=uri, neo4j_user=user, neo4j_password=pwd)
        result = hr.retrieve(req.question, top_k=req.top_k)
    except Exception as exc:
        # Fallback to standard query if hybrid is unavailable
        return _run_query(req.question, req.top_k, req.chunk_types, req.backend)

    context = result["combined_context"]
    backend = req.backend if req.backend != "auto" else detect_backend()

    try:
        if backend == "claude":
            answer = ask_claude(req.question, context)
        elif backend == "ollama":
            answer = ask_ollama(req.question, context)
        else:
            backend = "dry_run"
            answer = dry_run(req.question, context, result["chunks"])
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM backend error: {exc}")

    REQUEST_COUNT.labels(endpoint="/query/hybrid", backend=backend).inc()
    return HybridQueryResponse(
        question=req.question,
        backend=backend,
        chunks_retrieved=len(result["chunks"]),
        chunks=result["chunks"],
        graph_paths=result["graph_paths"],
        answer=answer,
    )


# ── Pipeline rebuild ──────────────────────────────────────────────────────────

@app.post("/pipeline/rebuild", response_model=RebuildResponse, tags=["pipeline"])
def trigger_rebuild():
    """Trigger the full graph rebuild pipeline asynchronously via Celery."""
    try:
        from graphrag.tasks import rebuild_pipeline
        result = rebuild_pipeline()
        return RebuildResponse(
            task_id=result.id,
            status="queued",
            message="Pipeline queued: build_graph -> chunk -> embed -> neo4j",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Celery unavailable. Is Redis running? Error: {exc}",
        )


@app.get("/pipeline/status/{task_id}", response_model=TaskStatusResponse, tags=["pipeline"])
def pipeline_status(task_id: str):
    """Check the status of a previously queued pipeline task."""
    try:
        from graphrag.tasks import celery_app
        result = celery_app.AsyncResult(task_id)
        return TaskStatusResponse(
            task_id=task_id,
            status=result.status,
            result=str(result.result) if result.result else None,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))
