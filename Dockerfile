FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for faiss-cpu and sentence-transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the sentence transformer model at build time
# Comment out if you want a lighter image and are OK with first-run download
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')" || true

# Copy application
COPY . .

EXPOSE 8001

CMD ["uvicorn", "graphrag.api:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
