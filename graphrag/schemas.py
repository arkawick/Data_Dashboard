"""
graphrag/schemas.py
===================
Pydantic models for the FastAPI query endpoint.
"""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="The question to answer")
    top_k: int = Field(20, ge=1, le=100, description="Number of chunks to retrieve")
    chunk_types: Optional[list[str]] = Field(
        None, description="Filter by chunk type: entity, relationship, neighborhood"
    )
    backend: str = Field("auto", description="LLM backend: auto, claude, ollama, dry_run")

    model_config = {"json_schema_extra": {"example": {
        "question": "Which employees are assigned to critical bugs?",
        "top_k": 20,
        "chunk_types": None,
        "backend": "auto",
    }}}


class ChunkModel(BaseModel):
    id: str
    type: str
    text: str
    keywords: list[str]
    node_id: Optional[str] = None
    source: Optional[str] = None
    target: Optional[str] = None


class QueryResponse(BaseModel):
    question: str
    backend: str
    chunks_retrieved: int
    chunks: list[dict[str, Any]]
    answer: str


class HybridQueryResponse(BaseModel):
    question: str
    backend: str
    chunks_retrieved: int
    chunks: list[dict[str, Any]]
    graph_paths: list[dict[str, Any]]
    answer: str


class HealthResponse(BaseModel):
    status: str
    chunks_loaded: int
    retriever_type: str
    neo4j_available: bool


class GraphStatsResponse(BaseModel):
    nodes: int
    edges: int
    node_types: dict[str, int]
    edge_types: dict[str, int]


class RebuildResponse(BaseModel):
    task_id: str
    status: str
    message: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[str] = None
