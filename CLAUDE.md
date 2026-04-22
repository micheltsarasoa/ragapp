# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Developer Environment

**The developer is on Windows.** When suggesting commands for the user to run in their terminal, always use Windows syntax:
- Delete a folder: `rmdir /s /q .venv` (cmd) or `Remove-Item -Recurse -Force .venv` (PowerShell) — never `rm -rf`
- Copy: `xcopy` or `copy` — never `cp`
- Paths: use backslashes (`apps\backend`) in user-facing commands
- Environment variables: `set VAR=value` (cmd) or `$env:VAR = "value"` (PowerShell)
- **npm / pnpm**: always invoke via full Windows path — `C:\Users\jms\AppData\Roaming\npm\npm` and `C:\Users\jms\AppData\Roaming\npm\pnpm`. Never rely on bare `npm` or `pnpm` — they fail in the bash tool on this machine.

## Development Commands

**Start services (local dev):**
```bash
# Vector DB (Qdrant)
docker run -d --name qdrantRagDb -p 6333:6333 -v ./qdrant_storage:/qdrant/storage qdrant/qdrant

# FastAPI backend
uv run uvicorn main:app

# Inngest event server (observability + async queue)
npx inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest --no-discovery

# Streamlit UI
uv run streamlit run streamlit_app.py
```

**Docker Compose (all services together):**
```bash
docker compose up --build
docker compose down
```

**Install dependencies:**
```bash
uv pip install -r requirements.txt
```

**No test suite or linting is configured.** There are no automated tests in this project.

## Architecture Overview

This is a RAG (Retrieval-Augmented Generation) app: users upload documents, which are chunked and stored as hybrid vectors, then query them via an LLM that answers using only the retrieved content.

### Service Map

| Service | Port | Role |
|---|---|---|
| Streamlit UI | 8501 | Multi-page frontend (upload, ask, manage) |
| FastAPI backend | 8000 | REST API + Inngest function host |
| Inngest dev server | 8288 | Async event queue + execution observability |
| Qdrant | 6333 | Hybrid vector store (dense + sparse) |
| SQLite (`ragapp.db`) | — | Document metadata + LLM config |

### Key Data Flows

**Ingestion:** File upload → `rag/ingest_pdf` Inngest event → `data_loader.py` chunks (1000 chars, 200 overlap) → fastembed produces dense (BAAI/bge-small-en-v1.5) + sparse (BM25) vectors → `vector_db.py` deduplicates and upserts to Qdrant → metadata persisted in SQLite → file deleted.

**Query — streaming path:** `GET /api/stream_query` → embed question same way → hybrid search in Qdrant with RRF fusion (filtered by user access) → truncate context to ~16K chars → build RAG prompt → stream NDJSON tokens directly from LLM (Groq/Ollama/custom).

**Query — observable path:** `rag/query_pdf_ai` Inngest event → same search + LLM logic but routed through Inngest for traceability.

### Access Control

No traditional auth. Users get an 8-char random hex key stored in the URL (`?key=...`). SHA-256 hash of the key becomes `user_id`. Documents can be `public` (visible to all) or `private` (only to owner). Qdrant search filters enforce this.

### LLM Configuration

Hot-swappable at runtime via `POST /api/llm_config`. Config is stored in SQLite with a `threading.Lock`. Supports any OpenAI-compatible endpoint (Groq, Ollama, custom). Default model: `llama3-8b-8192` on Groq.

### Rate Limiting (Inngest)

- Ingest: 2 req/min throttle, 1 per `source_id` per 4 hours
- Query: 10 req/min per `user_id`

## Key Files

- `main.py` — FastAPI app, all route handlers, and all Inngest function definitions
- `data_loader.py` — document reading (PDF/DOCX/TXT/MD), chunking, and embedding orchestration
- `vector_db.py` — Qdrant client wrapper: collection init, upsert, hybrid search
- `db.py` — SQLite schema and all metadata queries
- `custom_types.py` — Pydantic models shared across the app
- `auth.py` — access key → user_id resolution
- `streamlit_app.py` — main Streamlit entry point (upload + ask tabs)
- `pages/1_Manage_Documents.py` — document list/visibility/delete page

## Planned Migration

`docs/MIGRATION_PLAN.md` outlines decoupling the Streamlit UI into a React/Vite frontend with an expanded FastAPI surface (monorepo structure). The current codebase is still a flat-root Python monolith.

## Environment Variables

Copy `.env.example` to `.env`. Required: `GROQ_API_KEY` (or equivalent for your LLM provider). Qdrant and SQLite paths are configurable via env vars; defaults work for local dev.
