import datetime
import json
import logging
import os
from pathlib import Path
import threading
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import inngest
import inngest.fast_api
from openai import AsyncOpenAI, OpenAI
from pydantic import BaseModel

import db
from custom_types import RAGChunkAndSrc, RAGUpsertResult, RAGSearchResult
from data_loader import load_and_chunk, embed_dense, embed_sparse
from vector_db import get_qdrant_storage, build_access_filter

load_dotenv()
db.init_db()

# Conservative character budget for context passed to the LLM.
# llama3-8b-8192 has an 8 192-token window; reserving half for the answer.
_MAX_CONTEXT_CHARS = 4096 * 4  # ~4 096 tokens at ~4 chars/token


def _truncate_contexts(contexts: list[str]) -> list[str]:
    """Return as many context chunks as fit within the character budget."""
    result, used = [], 0
    for ctx in contexts:
        if used + len(ctx) > _MAX_CONTEXT_CHARS:
            break
        result.append(ctx)
        used += len(ctx)
    return result


def _build_rag_messages(question: str, contexts: list[str]) -> list[dict]:
    """Build the system + user messages list for a RAG query.

    Args:
        question: The user's question.
        contexts: Relevant context chunks retrieved from the vector store.

    Returns:
        A two-element list of chat message dicts ready for the LLM API.
    """
    context_block = "\n\n".join(f"- {c}" for c in contexts)
    return [
        {"role": "system", "content": "You answer questions using only the provided context."},
        {
            "role": "user",
            "content": (
                "Use the following context to answer the question.\n\n"
                f"Context:\n{context_block}\n\n"
                f"Question: {question}\n"
                "Answer concisely using the context above."
            ),
        },
    ]

# ---------------------------------------------------------------------------
# LLM config — mutable at runtime via POST /api/llm_config
# Persisted in SQLite so it survives restarts and is consistent across workers.
# A threading.Lock guards in-process concurrent writes within a single worker.
# ---------------------------------------------------------------------------

_llm_lock = threading.Lock()

_ENV_DEFAULTS: dict[str, str] = {
    "base_url": os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1"),
    "api_key": os.getenv("GROQ_API_KEY", ""),
    "model": os.getenv("LLM_MODEL", "llama3-8b-8192"),
}


def _get_llm_config() -> dict[str, str]:
    """Return current LLM config, preferring DB-stored values over env defaults."""
    with _llm_lock:
        stored = db.get_llm_config()
    return {**_ENV_DEFAULTS, **stored}


def _set_llm_config(config: dict[str, str]) -> None:
    with _llm_lock:
        db.set_llm_config(config)


def _sync_client() -> OpenAI:
    cfg = _get_llm_config()
    return OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])


def _async_client() -> AsyncOpenAI:
    cfg = _get_llm_config()
    return AsyncOpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])

inngest_client = inngest.Inngest(
    app_id="rag_app",
    logger=logging.getLogger("uvicorn"),
    is_production=False,
    serializer=inngest.PydanticSerializer(),
)


# ---------------------------------------------------------------------------
# Inngest function: Ingest document
# ---------------------------------------------------------------------------

@inngest_client.create_function(
    fn_id="RAG: Ingest Document",
    trigger=inngest.TriggerEvent(event="rag/ingest_pdf"),
    throttle=inngest.Throttle(limit=2, period=datetime.timedelta(minutes=1)),
    rate_limit=inngest.RateLimit(
        limit=1,
        period=datetime.timedelta(hours=4),
        key="event.data.source_id",
    ),
)
async def rag_ingest_pdf(ctx: inngest.Context):
    def _load(ctx: inngest.Context) -> RAGChunkAndSrc:
        pdf_path = ctx.event.data["pdf_path"]
        source_id = ctx.event.data.get("source_id", pdf_path)
        user_id = ctx.event.data.get("user_id", "anonymous")
        visibility = ctx.event.data.get("visibility", "private")
        chunks = load_and_chunk(pdf_path)
        return RAGChunkAndSrc(
            chunks=chunks, source_id=source_id, user_id=user_id, visibility=visibility
        )

    def _upsert(data: RAGChunkAndSrc) -> RAGUpsertResult:
        store = get_qdrant_storage()
        # Dedup: remove old vectors for this source before re-ingesting
        store.delete_by_source(data.source_id)

        dense_vecs = embed_dense(data.chunks)
        sparse_vecs = embed_sparse(data.chunks)
        ids = [
            str(uuid.uuid5(uuid.NAMESPACE_URL, f"{data.source_id}:{i}"))
            for i in range(len(data.chunks))
        ]
        payloads = [
            {
                "source": data.source_id,
                "text": data.chunks[i],
                "user_id": data.user_id,
                "visibility": data.visibility,
            }
            for i in range(len(data.chunks))
        ]
        store.upsert(ids, dense_vecs, sparse_vecs, payloads)

        # Persist metadata
        db.upsert_document(data.source_id, data.user_id, data.visibility, len(data.chunks))

        return RAGUpsertResult(ingested=len(data.chunks))

    chunks_and_src = await ctx.step.run(
        "load-and-chunk", lambda: _load(ctx), output_type=RAGChunkAndSrc
    )
    ingested = await ctx.step.run(
        "embed-and-upsert", lambda: _upsert(chunks_and_src), output_type=RAGUpsertResult
    )

    # Remove the uploaded file now that its content is safely in Qdrant.
    # Guard: only delete files inside the uploads/ directory.
    pdf_path = Path(ctx.event.data["pdf_path"])
    try:
        if "uploads" in pdf_path.parts:
            pdf_path.unlink(missing_ok=True)
    except OSError:
        pass  # non-fatal — stale files are cleaned up on next ingest

    return ingested.model_dump()


# ---------------------------------------------------------------------------
# Inngest function: Query (observable, non-streaming)
# ---------------------------------------------------------------------------

@inngest_client.create_function(
    fn_id="RAG: Query PDF",
    trigger=inngest.TriggerEvent(event="rag/query_pdf_ai"),
    rate_limit=inngest.RateLimit(
        limit=10,
        period=datetime.timedelta(minutes=1),
        key="event.data.user_id",
    ),
)
async def rag_query_pdf_ai(ctx: inngest.Context):
    question = ctx.event.data["question"]
    top_k = int(ctx.event.data.get("top_k", 5))
    user_id = ctx.event.data.get("user_id", "anonymous")

    def _search() -> RAGSearchResult:
        dense_vec = embed_dense([question])[0]
        sparse_vec = embed_sparse([question])[0]
        store = get_qdrant_storage()
        found = store.search(dense_vec, sparse_vec, top_k, build_access_filter(user_id))
        return RAGSearchResult(
            contexts=found["contexts"], sources=found["sources"], scores=found["scores"]
        )

    found = await ctx.step.run("embed-and-search", _search, output_type=RAGSearchResult)

    if not found.contexts:
        return {"answer": "No relevant documents found. Please upload a document first.", "sources": [], "scores": [], "num_contexts": 0}

    contexts = _truncate_contexts(found.contexts)
    messages = _build_rag_messages(question, contexts)

    def _llm_answer() -> dict:
        client = _sync_client()
        resp = client.chat.completions.create(
            model=_get_llm_config()["model"],
            max_tokens=1024,
            temperature=0.2,
            messages=messages,
        )
        return {"content": resp.choices[0].message.content.strip()}

    result = await ctx.step.run("llm-answer", _llm_answer)
    return {
        "answer": result["content"],
        "sources": found.sources,
        "scores": found.scores,
        "num_contexts": len(found.contexts),
    }


# ---------------------------------------------------------------------------
# FastAPI streaming endpoint (bypasses Inngest for real-time token output)
# ---------------------------------------------------------------------------

app = FastAPI()


@app.get("/api/stream_query")
async def stream_query(question: str, top_k: int = 5, user_id: str = "anonymous"):
    """Stream an LLM answer token-by-token using NDJSON."""
    dense_vec = embed_dense([question])[0]
    sparse_vec = embed_sparse([question])[0]
    store = get_qdrant_storage()
    found = store.search(dense_vec, sparse_vec, top_k, build_access_filter(user_id))

    if not found["contexts"]:
        async def _no_docs():
            yield json.dumps({"type": "error", "content": "No relevant documents found. Please upload a document first."}) + "\n"
        return StreamingResponse(_no_docs(), media_type="application/x-ndjson")

    contexts = _truncate_contexts(found["contexts"])
    messages = _build_rag_messages(question, contexts)

    async def generate():
        try:
            client = _async_client()
            stream = await client.chat.completions.create(
                model=_get_llm_config()["model"],
                max_tokens=1024,
                temperature=0.2,
                messages=messages,
                stream=True,
            )
            async for chunk in stream:
                token = chunk.choices[0].delta.content or ""
                if token:
                    yield json.dumps({"type": "token", "content": token}) + "\n"
            yield json.dumps({
                "type": "done",
                "sources": found["sources"],
                "scores": found["scores"],
            }) + "\n"
        except Exception as e:
            yield json.dumps({"type": "error", "content": str(e)}) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")


# ---------------------------------------------------------------------------
# LLM config endpoints
# ---------------------------------------------------------------------------

class LLMConfig(BaseModel):
    base_url: str
    api_key: str
    model: str


@app.get("/api/llm_config")
def get_llm_config_endpoint():
    """Return the active LLM config (API key masked)."""
    cfg = _get_llm_config()
    return {
        "base_url": cfg["base_url"],
        "model": cfg["model"],
        "api_key_set": bool(cfg["api_key"]),
    }


@app.post("/api/llm_config")
def set_llm_config_endpoint(cfg: LLMConfig):
    """Hot-swap the LLM provider without restarting the server."""
    _set_llm_config(cfg.model_dump())
    return {"status": "ok", "model": cfg.model, "base_url": cfg.base_url}


inngest.fast_api.serve(app, inngest_client, [rag_ingest_pdf, rag_query_pdf_ai])
