# RAG App – Production Readiness TODO

Generated from architecture review on 2026-04-17.

---

## BLOCKERS — Fix before any multi-user deployment

- [ ] **B1** Rotate `GROQ_API_KEY` and `HF_TOKEN`; verify `.env` is not in git history (`git log --all --full-history -- .env`)
- [ ] **B2** `user_id` accepted as plain unauthenticated query param in `/api/stream_query` — any caller can read another user's private docs (`main.py:180`)
- [ ] **B3** `source_id` is a bare filename used as primary key — uploading same-named file as another user permanently destroys their data in Qdrant and SQLite (`main.py:66`, `db.py`)
- [ ] **B4** `POST /api/llm_config` is unauthenticated — anyone on the network can redirect LLM traffic or drain the API budget

---

## HIGH PRIORITY — Fix before production traffic

- [x] **H1** Add Qdrant payload indexes on `user_id`, `visibility`, `source` — currently full-collection scans on every query (`vector_db.py`)
- [x] **H2** No token budget guard — `top_k=20` with 1000-char chunks can exceed the 8k model context window, causing `400` errors (`main.py`)
- [x] **H3** No empty-context guard — LLM hallucinates when the querying user has no indexed documents (`main.py`)
- [x] **H4** `QdrantStorage()` instantiated per-request with a network round-trip — use a singleton via `@lru_cache` (`vector_db.py`)
- [x] **H5** `_active_llm` dict is not thread-safe and is process-local — silently broken under multi-worker uvicorn (`main.py`)
- [x] **H6** Uploaded files in `uploads/` are never deleted after ingestion — unbounded disk growth (`main.py`, `streamlit_app.py`)

---

## MEDIUM PRIORITY — Address for stability

- [x] **M1** `source_id: str = None` wrong type annotation — should be `str | None = None` (`custom_types.py`)
- [x] **M2** `asyncio.run()` inside Streamlit upload callback is fragile when an event loop is already running (`streamlit_app.py`)
- [x] **M3** `SparseIndexParams(on_disk=False)` will cause Qdrant OOM at scale (`vector_db.py`)
- [x] **M4** `DB_PATH = Path("ragapp.db")` is CWD-relative — breaks under Docker/systemd (`db.py`)
- [x] **M5** Prompt construction duplicated between `rag_query_pdf_ai` and `stream_query` — extract to shared function (`main.py`)
- [x] **M6** `sources` returned as a `set()` in `QdrantStorage.search()` — non-deterministic ordering, breaks score alignment (`vector_db.py`)
- [x] **M7** TXT/MD reader hard-codes UTF-8 — will raise `UnicodeDecodeError` on Windows-encoded files (`data_loader.py`)
- [x] **M8** `fetch_runs` polling in Streamlit has no HTTP timeout — can hang indefinitely (`streamlit_app.py`)

---

## MANAGE DOCUMENTS PAGE — `pages/1_Manage_Documents.py`

### Critical

- [x] **MD-C1** `db.update_visibility` and `db.delete_document` have no `user_id` WHERE clause — any caller who knows a `source_id` can delete or modify another user's document (`db.py:61-71`, page `L78,L99`)

### High

- [x] **MD-H1** XSS — `source_id` (user-supplied filename) interpolated raw into `unsafe_allow_html=True` HTML (`page:L65`) — escape with `html.escape()`
- [x] **MD-H2** Non-atomic two-store mutations — SQLite updated before Qdrant on visibility toggle; failure between stores leaves ACL out of sync (`page:L78-90`)
- [x] **MD-H3** `from qdrant_client.models import ...` inside a button callback; raw `qs.client.set_payload()` belongs in `QdrantStorage` as `update_source_visibility()` (`page:L82-90`, `vector_db.py`)

### Medium

- [x] **MD-M1** `QdrantStorage()` instantiated per button click, firing a `collection_exists()` network call each time — use `@st.cache_resource` factory (`page:L80,L96`)
- [x] **MD-M2** Delete fires immediately with no confirmation dialog — add two-click confirm via `st.session_state` (`page:L94-99`)
- [x] **MD-M3** `db.init_db()` runs on every Streamlit rerun — wrap in `@st.cache_resource` (`page:L14`)

### Low

- [x] **MD-L1** `ingested_at[:19]` silently truncates or crashes on unexpected DB values — use `datetime.fromisoformat()` with fallback (`page:L45`)
