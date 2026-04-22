"""Pre-download fastembed ONNX models into the project-local cache.

Run this once before starting uvicorn for the first time:
    uv run python download_models.py

After this completes, uvicorn will start instantly with no network access needed.
"""

# Load .env (including HF_TOKEN) before any HuggingFace code runs.
from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv(usecwd=True))

from app.core.config import FASTEMBED_CACHE_PATH

print(f"Downloading models to: {FASTEMBED_CACHE_PATH}\n")

from fastembed import TextEmbedding, SparseTextEmbedding

print("1/2  Dense model (BAAI/bge-small-en-v1.5) — ~130 MB, please wait...")
TextEmbedding("BAAI/bge-small-en-v1.5", cache_dir=FASTEMBED_CACHE_PATH)
print("     Done.\n")

print("2/2  Sparse model (Qdrant/bm25) — ~25 KB...")
SparseTextEmbedding("Qdrant/bm25", cache_dir=FASTEMBED_CACHE_PATH)
print("     Done.\n")

print("All models cached. You can now run uvicorn app.main:app.")
