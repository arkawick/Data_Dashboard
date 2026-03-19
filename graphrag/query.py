"""
graphrag/query.py
=================
GraphRAG query interface — works with or without an API key.

Modes (auto-detected):
  1. Dry-run   - no key needed; prints retrieved chunks + full prompt
  2. Claude    - set ANTHROPIC_API_KEY in environment
  3. Ollama    - set OLLAMA_MODEL (e.g. "llama3") to use a local model

Usage:
    python graphrag/query.py                        # interactive CLI
    python graphrag/query.py "your question here"   # single shot

Setting up a key later:
    Windows:  set ANTHROPIC_API_KEY=sk-ant-...
    Linux:    export ANTHROPIC_API_KEY=sk-ant-...
"""

import os
import sys
import textwrap

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from graphrag.retriever import GraphRetriever

MODEL      = "claude-sonnet-4-6"
TOP_K      = 20
MAX_TOKENS = 1024

SYSTEM_PROMPT = """You are a GraphRAG assistant for a software engineering knowledge graph.

The graph contains 5 node types:
  Employee    - employee_id, name, role, team, department, seniority, skills
  Project     - project_id, project_name, domain, status, priority, tech_stack, lead_name
  TestCase    - test_case_id, test_case_name, status, test_type, automation_status
  Bug         - bug_id, title, severity, priority, status, bug_type
  Requirement - requirement_id, requirement_name, category, priority, status

And 10 relationship types:
  Employee  -[LEADS]-----------> Project
  Employee  -[ASSIGNED_TO]-----> TestCase
  Employee  -[REPORTED]--------> Bug
  Employee  -[ASSIGNED_BUG]----> Bug
  Employee  -[RESPONSIBLE_FOR]-> Requirement
  Project   -[HAS_TEST_CASE]---> TestCase
  Project   -[HAS_BUG]---------> Bug
  Project   -[HAS_REQUIREMENT]-> Requirement
  TestCase  -[FOUND_BUG]-------> Bug
  TestCase  -[COVERS]----------> Requirement

Answer using ONLY the graph context provided. Be specific about IDs and names.
If the context is insufficient, say so clearly.
"""


def build_prompt(question, context):
    sep = "-" * 60
    return f"Graph context:\n{sep}\n{context}\n{sep}\n\nQuestion: {question}"


# ── backends ──────────────────────────────────────────────────────────────────

def ask_claude(question, context):
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_prompt(question, context)}],
    )
    return resp.content[0].text


def ask_ollama(question, context):
    import urllib.request, json
    model = os.environ.get("OLLAMA_MODEL", "llama3")
    payload = json.dumps({
        "model": model,
        "prompt": SYSTEM_PROMPT + "\n\n" + build_prompt(question, context),
        "stream": False,
    }).encode()
    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["response"]


def dry_run(question, context, chunks):
    """Print retrieved chunks and the full prompt -- no LLM needed."""
    lines = [
        "",
        "=" * 60,
        "  DRY-RUN MODE  (no API key set)",
        "=" * 60,
        f"\nQuestion: {question}",
        f"\nRetrieved {len(chunks)} chunks:",
    ]
    for i, c in enumerate(chunks, 1):
        lines.append(f"  [{i:02}] ({c['type']:12}) {c['id']}")
        lines.append(f"       " + c["text"][:100] + ("..." if len(c["text"]) > 100 else ""))

    lines += [
        "\n" + "-" * 60,
        "FULL PROMPT THAT WOULD BE SENT TO LLM:",
        "-" * 60,
        SYSTEM_PROMPT,
        build_prompt(question, context),
        "-" * 60,
        "\nTo enable live answers:",
        "  Claude : set ANTHROPIC_API_KEY=sk-ant-...",
        "  Ollama  : set OLLAMA_MODEL=llama3  (and run: ollama serve)",
        "",
    ]
    return "\n".join(lines)


# ── router ────────────────────────────────────────────────────────────────────

def detect_backend():
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "claude"
    if os.environ.get("OLLAMA_MODEL"):
        return "ollama"
    return "dry_run"


def ask(question, retriever):
    chunks  = retriever.retrieve(question, top_k=TOP_K)
    context = "\n\n".join(f"[{i+1}] ({c['type']}) {c['text']}" for i, c in enumerate(chunks))
    backend = detect_backend()

    if backend == "claude":
        return f"[Claude]\n\n{ask_claude(question, context)}"
    if backend == "ollama":
        model = os.environ.get("OLLAMA_MODEL", "llama3")
        return f"[Ollama/{model}]\n\n{ask_ollama(question, context)}"
    return dry_run(question, context, chunks)


# ── CLI ───────────────────────────────────────────────────────────────────────

EXAMPLE_QUESTIONS = [
    "Which employees are assigned to critical bugs?",
    "Which project has the most open bugs?",
    "List all requirements in the Finance domain and their verification owners.",
    "Which test cases cover security requirements?",
    "Who leads projects in the Healthcare domain?",
    "Show all failed test cases assigned to senior engineers.",
    "Which bugs were reported and also assigned to the same employee?",
    "What is the status of requirements in the Platform Modernization project?",
]


def main():
    retriever = GraphRetriever()
    backend   = detect_backend()

    print(f"\nGraphRAG Query Interface")
    print(f"  Chunks indexed : {len(retriever.chunks)}")
    print(f"  Backend        : {backend}")
    if backend == "dry_run":
        print(f"  (Set ANTHROPIC_API_KEY or OLLAMA_MODEL to get LLM answers)")
    print()

    # Single-question mode
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        print(ask(question, retriever))
        return

    # Show example questions
    print("Example questions:")
    for i, q in enumerate(EXAMPLE_QUESTIONS, 1):
        print(f"  {i}. {q}")
    print("\nType a question, a number (1-8) to use an example, or 'q' to quit.\n")

    while True:
        try:
            raw = input("Q: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not raw or raw.lower() == "q":
            break
        if raw.isdigit() and 1 <= int(raw) <= len(EXAMPLE_QUESTIONS):
            question = EXAMPLE_QUESTIONS[int(raw) - 1]
            print(f"   → {question}")
        else:
            question = raw

        print(ask(question, retriever))
        print()


if __name__ == "__main__":
    main()
