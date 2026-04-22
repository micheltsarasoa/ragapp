import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.core.data_loader import embed_dense, embed_sparse
from app.core.llm import get_llm_config, async_client, truncate_contexts, build_rag_messages
from app.core.vector_db import get_qdrant_storage, build_access_filter

router = APIRouter()


@router.get("/api/stream_query")
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

    contexts = truncate_contexts(found["contexts"])
    messages = build_rag_messages(question, contexts)

    async def generate():
        try:
            client = async_client()
            stream = await client.chat.completions.create(
                model=get_llm_config()["model"],
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
