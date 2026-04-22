import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

# find_dotenv(usecwd=True) walks up from the current working directory until it
# finds a .env file — picks up the root-level .env regardless of which
# subdirectory uvicorn / scripts are launched from.
load_dotenv(find_dotenv(usecwd=True))

# Stable model cache — keeps fastembed weights out of the OS temp folder,
# which Windows can delete mid-download, corrupting the ONNX snapshot.
# Default: <repo>/apps/backend/.fastembed_cache (project-local, gitignored).
_default_cache = str(Path(__file__).parent.parent.parent / ".fastembed_cache")
FASTEMBED_CACHE_PATH: str = os.getenv("FASTEMBED_CACHE_PATH", _default_cache)
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
MAX_CONTEXT_CHARS: int = 4096 * 4  # ~4 096 tokens at ~4 chars/token

ENV_LLM_DEFAULTS: dict[str, str] = {
    "base_url": os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1"),
    "api_key": os.getenv("GROQ_API_KEY", ""),
    "model": os.getenv("LLM_MODEL", "llama3-8b-8192"),
}
