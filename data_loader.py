from pathlib import Path

from fastembed import TextEmbedding, SparseTextEmbedding
from llama_index.readers.file import PDFReader, DocxReader
from llama_index.core.node_parser import SentenceSplitter

DENSE_MODEL = "BAAI/bge-small-en-v1.5"
SPARSE_MODEL = "Qdrant/bm25"
EMBED_DIM = 384

# Models are loaded once at import time; fastembed caches weights locally.
_dense_encoder = TextEmbedding(DENSE_MODEL)
_sparse_encoder = SparseTextEmbedding(SPARSE_MODEL)

splitter = SentenceSplitter(chunk_size=1000, chunk_overlap=200)

_SUPPORTED = {".pdf", ".docx", ".txt", ".md"}


def load_and_chunk(path: str) -> list[str]:
    """Load a document and return a list of text chunks.

    Supported formats: PDF, DOCX, TXT, MD.
    """
    p = Path(path)
    ext = p.suffix.lower()
    if ext not in _SUPPORTED:
        raise ValueError(f"Unsupported file type '{ext}'. Supported: {', '.join(_SUPPORTED)}")

    if ext == ".pdf":
        docs = PDFReader().load_data(file=p)
        texts = [d.text for d in docs if getattr(d, "text", None)]
    elif ext == ".docx":
        docs = DocxReader().load_data(file=p)
        texts = [d.text for d in docs if getattr(d, "text", None)]
    else:  # .txt / .md
        texts = [p.read_text(encoding="utf-8")]

    chunks: list[str] = []
    for t in texts:
        chunks.extend(splitter.split_text(t))
    return chunks


def embed_dense(texts: list[str]) -> list[list[float]]:
    """Return 384-dim dense vectors (BAAI/bge-small-en-v1.5)."""
    return [vec.tolist() for vec in _dense_encoder.embed(texts)]


def embed_sparse(texts: list[str]) -> list[dict]:
    """Return sparse BM25 vectors as {indices, values} dicts."""
    result = []
    for sv in _sparse_encoder.embed(texts):
        result.append({"indices": sv.indices.tolist(), "values": sv.values.tolist()})
    return result
