import datetime
import uuid
from pathlib import Path

import inngest

from app.core import db
from app.core.data_loader import load_and_chunk, embed_dense, embed_sparse
from app.core.vector_db import get_qdrant_storage
from app.inngest_functions.client import inngest_client
from app.models.rag import RAGChunkAndSrc, RAGUpsertResult


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
        db.upsert_document(data.source_id, data.user_id, data.visibility, len(data.chunks))
        return RAGUpsertResult(ingested=len(data.chunks))

    chunks_and_src = await ctx.step.run(
        "load-and-chunk", lambda: _load(ctx), output_type=RAGChunkAndSrc
    )
    ingested = await ctx.step.run(
        "embed-and-upsert", lambda: _upsert(chunks_and_src), output_type=RAGUpsertResult
    )

    pdf_path = Path(ctx.event.data["pdf_path"])
    try:
        if "uploads" in pdf_path.parts:
            pdf_path.unlink(missing_ok=True)
    except OSError:
        pass

    return ingested.model_dump()
