"""
airflow/dags/graphrag_on_demand_dag.py
=======================================
On-demand Airflow DAG for the GraphRAG pipeline.
No schedule -- triggered manually from the Airflow UI or REST API.

Useful when:
  - Data was updated outside the nightly schedule
  - A rebuild was triggered from the Django dashboard
  - Debugging or testing individual pipeline steps

Trigger via Airflow REST API:
    curl -X POST http://localhost:8080/api/v1/dags/graphrag_on_demand/dagRuns \
         -H "Content-Type: application/json" \
         -u admin:admin \
         -d '{"conf": {"reason": "manual"}}'

Or from the Airflow UI: DAGs -> graphrag_on_demand -> Trigger DAG
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
    "retries":          1,
    "retry_delay":      timedelta(minutes=2),
    "email_on_failure": False,
}

with DAG(
    dag_id="graphrag_on_demand",
    default_args=default_args,
    description="Manual trigger: rebuild graph, chunks, embed, and reload Neo4j",
    schedule=None,            # No schedule -- on-demand only
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["graphrag", "on-demand"],
) as dag:

    build = BashOperator(
        task_id="build_graph",
        bash_command=f"cd {PROJECT_ROOT} && {PYTHON} graphrag/build_graph.py",
        env={
            "MONGO_URI": os.environ.get("MONGO_URI", "mongodb://mongo:27017/"),
            "DB_NAME":   os.environ.get("DB_NAME",   "test_db"),
        },
    )

    chunk = BashOperator(
        task_id="chunk_graph",
        bash_command=f"cd {PROJECT_ROOT} && {PYTHON} graphrag/chunk_graph.py",
    )

    embed = BashOperator(
        task_id="embed_chunks",
        bash_command=f"cd {PROJECT_ROOT} && {PYTHON} graphrag/embed_chunks.py || echo 'Embed skipped'",
    )

    neo4j = BashOperator(
        task_id="load_neo4j",
        bash_command=f"cd {PROJECT_ROOT} && {PYTHON} graphrag/load_neo4j.py",
        env={
            "NEO4J_URI":      os.environ.get("NEO4J_URI",      "bolt://neo4j:7687"),
            "NEO4J_USER":     os.environ.get("NEO4J_USER",     "neo4j"),
            "NEO4J_PASSWORD": os.environ.get("NEO4J_PASSWORD", "password"),
        },
    )

    def _done(**context):
        conf = context.get("dag_run").conf or {}
        reason = conf.get("reason", "not specified")
        print(f"[graphrag_on_demand] Pipeline complete. Reason: {reason}")

    done = PythonOperator(
        task_id="done",
        python_callable=_done,
    )

    build >> chunk >> embed >> neo4j >> done
