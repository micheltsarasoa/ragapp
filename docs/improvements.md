# Improvements

All 11 improvements have been implemented.

---

## Implemented

### 1. ✅ Local embeddings (fastembed)
**`data_loader.py`** — Replaced OpenAI embeddings with `fastembed`.
- Dense model: `BAAI/bge-small-en-v1.5` (384 dims, ~130 MB, runs locally)
- Sparse model: `Qdrant/bm25` (for hybrid search)
- No API key required for embeddings

### 2. ✅ Groq LLM
**`main.py`** — Switched from `gpt-4o-mini` to Groq's `llama3-8b-8192` via the OpenAI-compatible API.
- Configurable via `LLM_MODEL` env var
- Get a free API key at https://console.groq.com

### 3. ✅ Query rate limiting
**`main.py`** — Added `RateLimit` to `rag_query_pdf_ai`: 10 requests/min per `user_id`.

### 4. ✅ Deduplication before re-ingest
**`main.py`** + **`vector_db.py`** — Before upserting, `delete_by_source()` removes all existing vectors for the same `source_id`. Re-uploading the same file cleanly replaces all old chunks.

### 5. ✅ Streaming LLM responses
**`main.py`** — New `GET /api/stream_query` endpoint streams tokens as NDJSON.
**`streamlit_app.py`** — "Stream answer" checkbox uses `st.write_stream()` for real-time output. The Inngest (non-streaming, observable) mode is still available via the checkbox.

### 6. ✅ Chunk scores in the UI
**`vector_db.py`** — `search()` now returns `scores` alongside contexts and sources.
**`custom_types.py`** — `RAGSearchResult` includes `scores: list[float]`.
**`streamlit_app.py`** — Scores displayed next to each source name.

### 7. ✅ More file types
**`data_loader.py`** — `load_and_chunk()` (renamed from `load_and_chunk_pdf`) supports PDF, DOCX, TXT, and MD.
**`streamlit_app.py`** — File uploader accepts all four types.

### 8. ✅ SQLite metadata persistence
**`db.py`** (new) — Stores `{source_id, user_id, visibility, ingested_at, chunk_count}` in `ragapp.db`.
**`main.py`** — Writes to DB on every successful ingest.

### 9. ✅ Docker Compose
**`Dockerfile`** + **`docker-compose.yml`** — Containerises Qdrant, FastAPI backend, and Streamlit UI. Run with `docker compose up --build`.

### 10. ✅ Document management page
**`pages/1_Manage_Documents.py`** (new) — Streamlit multipage sidebar page.
- Lists all documents visible to the current user
- Toggle visibility: private ↔ public (updates both SQLite and Qdrant payloads)
- Delete document (removes from Qdrant and SQLite)

### 11. ✅ Hybrid search (dense + BM25)
**`vector_db.py`** — Collection now uses named vectors: `dense` (384-dim cosine) + `sparse` (BM25).
Search uses Qdrant's `query_points` with `Prefetch` + `FusionQuery(RRF)` for hybrid re-ranking.

> **Migration note:** The Qdrant collection schema changed. If upgrading from the original version, reset the database:
> ```bash
> docker stop qdrantRagDb && docker rm qdrantRagDb
> rm -rf qdrant_storage ragapp.db
> ```

---

## Access control

See `docs/access-control.md` for the full design. In summary:
- Every ingested chunk carries `user_id` and `visibility` in its Qdrant payload
- Queries apply a `should` filter: `visibility == "public" OR user_id == <current_user>`
- User identity is a random UUID per browser session stored in `st.session_state`
