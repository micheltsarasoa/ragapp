from pathlib import Path

from fastembed import TextEmbedding, SparseTextEmbedding
from llama_index.readers.file import PDFReader, DocxReader
from llama_index.core.node_parser import SentenceSplitter

from app.core.config import FASTEMBED_CACHE_PATH

DENSE_MODEL = "BAAI/bge-small-en-v1.5"
SPARSE_MODEL = "Qdrant/bm25"
EMBED_DIM = 384

_dense_encoder = TextEmbedding(DENSE_MODEL, cache_dir=FASTEMBED_CACHE_PATH)
_sparse_encoder = SparseTextEmbedding(SPARSE_MODEL, cache_dir=FASTEMBED_CACHE_PATH)

splitter = SentenceSplitter(chunk_size=1000, chunk_overlap=200)

_SUPPORTED = {".pdf", ".docx", ".txt", ".md"}


def _read_text(p: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return p.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not decode {p.name} with any supported encoding (utf-8, utf-8-sig, latin-1)")


def load_and_chunk(path: str) -> list[str]:
    """Load a document and return a list of text chunks."""
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
    else:
        texts = [_read_text(p)]

    chunks: list[str] = []
    for t in texts:
        chunks.extend(splitter.split_text(t))
    return chunks


def embed_dense(texts: list[str]) -> list[list[float]]:
    return [vec.tolist() for vec in _dense_encoder.embed(texts)]


def embed_sparse(texts: list[str]) -> list[dict]:
    result = []
    for sv in _sparse_encoder.embed(texts):
        result.append({"indices": sv.indices.tolist(), "values": sv.values.tolist()})
    return result
