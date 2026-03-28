"""
airflow/dags/graphrag_pipeline_dag.py
======================================
Nightly Airflow DAG for the GraphRAG pipeline.

Schedule: 2:00 AM UTC daily

Pipeline steps:
  1. seed_mongodb     - generate fresh test data
  2. build_graph      - MongoDB -> NetworkX -> graph.gpickle + graph.json
  3. chunk_graph      - graph.gpickle -> chunks.json
  4. embed_chunks     - chunks.json -> chunks.faiss (FAISS semantic index)
  5. load_neo4j       - graph.gpickle -> Neo4j
  6. notify           - log completion summary

Access Airflow UI at http://localhost:8080 (admin/admin)

Setup:
  docker compose up airflow-webserver airflow-scheduler airflow-init
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

PROJECT_ROOT = os.environ.get("PROJECT_ROOT", "/app")
PYTHON       = os.environ.get("AIRFLOW_PYTHON", "python")

default_args = {
    "owner":            "graphrag",
    "retries":          2,
    "retry_delay":      timedelta(minutes=5),
    "email_on_failure": False,
    "email_on_retry":   False,
}

with DAG(
    dag_id="graphrag_nightly_pipeline",
    default_args=default_args,
    description="Nightly: seed -> build graph -> chunk -> embed -> neo4j reload",
    schedule="0 2 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["graphrag", "nightly"],
) as dag:

    t1_seed = BashOperator(
        task_id="seed_mongodb",
        bash_command=f"cd {PROJECT_ROOT} && {PYTHON} generate_data.py",
        env={
            "MONGO_URI": os.environ.get("MONGO_URI", "mongodb://mongo:27017/"),
            "DB_NAME":   os.environ.get("DB_NAME",   "test_db"),
        },
    )

    t2_build = BashOperator(
        task_id="build_graph",
        bash_command=f"cd {PROJECT_ROOT} && {PYTHON} graphrag/build_graph.py",
        env={
            "MONGO_URI": os.environ.get("MONGO_URI", "mongodb://mongo:27017/"),
            "DB_NAME":   os.environ.get("DB_NAME",   "test_db"),
        },
    )

    t3_chunk = BashOperator(
        task_id="chunk_graph",
        bash_command=f"cd {PROJECT_ROOT} && {PYTHON} graphrag/chunk_graph.py",
    )

    t4_embed = BashOperator(
        task_id="embed_chunks",
        bash_command=f"cd {PROJECT_ROOT} && {PYTHON} graphrag/embed_chunks.py || echo 'Embed skipped'",
    )

    t5_neo4j = BashOperator(
        task_id="load_neo4j",
        bash_command=f"cd {PROJECT_ROOT} && {PYTHON} graphrag/load_neo4j.py",
        env={
            "NEO4J_URI":      os.environ.get("NEO4J_URI",      "bolt://neo4j:7687"),
            "NEO4J_USER":     os.environ.get("NEO4J_USER",     "neo4j"),
            "NEO4J_PASSWORD": os.environ.get("NEO4J_PASSWORD", "password"),
        },
    )

    def _notify_completion(**context):
        import json
        run_id = context.get("run_id", "unknown")
        graph_json = os.path.join(PROJECT_ROOT, "graphrag", "graph.json")
        if os.path.exists(graph_json):
            with open(graph_json, encoding="utf-8") as f:
                data = json.load(f)
            stats = data.get("stats", {})
            nodes = stats.get("nodes", "?")
            edges = stats.get("edges", "?")
        else:
            nodes = edges = "?"
        print(f"[graphrag_nightly_pipeline] Complete. run_id={run_id}")
        print(f"  Graph: {nodes} nodes, {edges} edges")

    t6_notify = PythonOperator(
        task_id="notify_completion",
        python_callable=_notify_completion,
    )

    # DAG dependency chain
    t1_seed >> t2_build >> t3_chunk >> t4_embed >> t5_neo4j >> t6_notify
