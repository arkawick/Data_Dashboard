"""
graphrag/embed_chunks.py
========================
Builds a FAISS semantic index over all text chunks.
Run this once after chunk_graph.py to enable semantic search.

Requirements:
    pip install faiss-cpu sentence-transformers

Output:
    graphrag/chunks.faiss   -- FAISS IndexFlatIP (cosine similarity via L2-normalised vectors)
    graphrag/id_map.json    -- maps FAISS int index -> chunks.json list index

Run:
    python graphrag/embed_chunks.py
"""

import json
import os

CHUNKS_PATH = os.path.join(os.path.dirname(__file__), "chunks.json")
FAISS_PATH  = os.path.join(os.path.dirname(__file__), "chunks.faiss")
IDMAP_PATH  = os.path.join(os.path.dirname(__file__), "id_map.json")

MODEL_NAME  = "all-MiniLM-L6-v2"   # 384-dim, ~90MB, fast on CPU
BATCH_SIZE  = 64


def build_faiss_index(chunks_path=CHUNKS_PATH, faiss_path=FAISS_PATH, idmap_path=IDMAP_PATH):
    try:
        import faiss
        import numpy as np
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        raise ImportError(
            f"Missing dependency: {e}\n"
            "Install with: pip install faiss-cpu sentence-transformers"
        )

    print(f"Loading chunks from {chunks_path}...")
    with open(chunks_path, encoding="utf-8") as f:
        chunks = json.load(f)
    print(f"  {len(chunks)} chunks loaded")

    texts = [c["text"] for c in chunks]

    print(f"Loading sentence transformer model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    print(f"Encoding {len(texts)} chunks (batch_size={BATCH_SIZE})...")
    embeddings = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
    )

    # L2-normalise so inner product == cosine similarity
    embeddings = embeddings.astype("float32")
    faiss.normalize_L2(embeddings)

    dim = embeddings.shape[1]
    print(f"  Embedding shape: {embeddings.shape}, dim={dim}")

    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    print(f"  FAISS index size: {index.ntotal} vectors")

    faiss.write_index(index, faiss_path)
    print(f"Saved FAISS index -> {faiss_path}")

    # id_map: FAISS int -> chunks list index (identity mapping since we added in order)
    id_map = list(range(len(chunks)))
    with open(idmap_path, "w", encoding="utf-8") as f:
        json.dump(id_map, f)
    print(f"Saved id map      -> {idmap_path}")

    return index


if __name__ == "__main__":
    build_faiss_index()
    print("\nDone. You can now run query.py with semantic search enabled.")
