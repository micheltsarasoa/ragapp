import datetime

import inngest

from app.core.data_loader import embed_dense, embed_sparse
from app.core.llm import get_llm_config, sync_client, truncate_contexts, build_rag_messages
from app.core.vector_db import get_qdrant_storage, build_access_filter
from app.inngest_functions.client import inngest_client
from app.models.rag import RAGSearchResult


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

    contexts = truncate_contexts(found.contexts)
    messages = build_rag_messages(question, contexts)

    def _llm_answer() -> dict:
        client = sync_client()
        resp = client.chat.completions.create(
            model=get_llm_config()["model"],
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
