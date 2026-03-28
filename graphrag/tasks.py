"""
graphrag/tasks.py
=================
Celery task definitions for asynchronous graph pipeline execution.

Tasks:
    task_build_graph   -- MongoDB -> NetworkX -> graph.gpickle + graph.json
    task_chunk_graph   -- graph.gpickle -> chunks.json
    task_embed_chunks  -- chunks.json -> chunks.faiss (optional: needs sentence-transformers)
    task_load_neo4j    -- graph.gpickle -> Neo4j

Trigger full pipeline:
    from graphrag.tasks import rebuild_pipeline
    result = rebuild_pipeline()        # returns AsyncResult
    print(result.id)                   # task chain ID

Start worker:
    celery -A graphrag.tasks worker --loglevel=info

Nightly schedule (configured here, activated by celery beat):
    celery -A graphrag.tasks beat --loglevel=info
"""

import os
from celery import Celery, chain
from celery.schedules import crontab

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "graphrag_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    result_expires=86400,     # 24 hours
    worker_redirect_stdouts_level="INFO",
)

# ── Nightly schedule via Celery Beat ─────────────────────────────────────────

celery_app.conf.beat_schedule = {
    "nightly-graph-rebuild": {
        "task": "graphrag.tasks.task_full_pipeline",
        "schedule": crontab(hour=2, minute=0),  # 2:00 AM UTC
    },
}


# ── Task definitions ──────────────────────────────────────────────────────────

@celery_app.task(bind=True, name="graphrag.tasks.task_build_graph", max_retries=2)
def task_build_graph(self):
    """Build NetworkX graph from MongoDB and save graph.gpickle + graph.json."""
    try:
        from graphrag.build_graph import build
        G = build()
        result = {"nodes": G.number_of_nodes(), "edges": G.number_of_edges()}
        print(f"[task_build_graph] Done: {result}")
        return result
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(bind=True, name="graphrag.tasks.task_chunk_graph", max_retries=2)
def task_chunk_graph(self, prev_result=None):
    """Convert graph.gpickle to text chunks.json."""
    try:
        from graphrag.chunk_graph import main as chunk_main
        chunk_main()
        print("[task_chunk_graph] Done")
        return "chunked"
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(bind=True, name="graphrag.tasks.task_embed_chunks", max_retries=1)
def task_embed_chunks(self, prev_result=None):
    """Build FAISS index from chunks.json (requires sentence-transformers)."""
    try:
        from graphrag.embed_chunks import build_faiss_index
        build_faiss_index()
        print("[task_embed_chunks] Done")
        return "embedded"
    except ImportError:
        print("[task_embed_chunks] Skipped: sentence-transformers not installed")
        return "skipped"
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, name="graphrag.tasks.task_load_neo4j", max_retries=2)
def task_load_neo4j(self, prev_result=None):
    """Load graph.gpickle into Neo4j."""
    try:
        from graphrag.load_neo4j import main as neo4j_main
        neo4j_main()
        print("[task_load_neo4j] Done")
        return "neo4j_loaded"
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(bind=True, name="graphrag.tasks.task_full_pipeline")
def task_full_pipeline(self):
    """Run the full pipeline synchronously (used by celery beat nightly schedule)."""
    results = {}

    try:
        from graphrag.build_graph import build
        G = build()
        results["build"] = {"nodes": G.number_of_nodes(), "edges": G.number_of_edges()}
    except Exception as exc:
        results["build"] = f"FAILED: {exc}"
        return results

    try:
        from graphrag.chunk_graph import main as chunk_main
        chunk_main()
        results["chunk"] = "ok"
    except Exception as exc:
        results["chunk"] = f"FAILED: {exc}"
        return results

    try:
        from graphrag.embed_chunks import build_faiss_index
        build_faiss_index()
        results["embed"] = "ok"
    except ImportError:
        results["embed"] = "skipped (no sentence-transformers)"
    except Exception as exc:
        results["embed"] = f"FAILED: {exc}"

    try:
        from graphrag.load_neo4j import main as neo4j_main
        neo4j_main()
        results["neo4j"] = "ok"
    except Exception as exc:
        results["neo4j"] = f"FAILED: {exc}"

    print(f"[task_full_pipeline] Complete: {results}")
    return results


# ── Helper to chain tasks ─────────────────────────────────────────────────────

def rebuild_pipeline():
    """
    Queue the full pipeline as a Celery task chain.
    Returns AsyncResult (use .id to poll status).
    """
    return chain(
        task_build_graph.s(),
        task_chunk_graph.s(),
        task_embed_chunks.s(),
        task_load_neo4j.s(),
    ).apply_async()
