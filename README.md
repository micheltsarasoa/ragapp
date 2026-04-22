# ragapp

A Retrieval-Augmented Generation (RAG) application. Upload PDF, DOCX, TXT, or MD documents and ask questions — the AI answers using only the content of your documents.

**Stack:** FastAPI · Inngest · Qdrant · React/Vite · Groq LLM · fastembed (local embeddings)

---

## Table of contents

1. [How it works](#how-it-works)
2. [Prerequisites](#prerequisites)
3. [Quick start](#quick-start)
4. [Project structure](#project-structure)
5. [Environment variables](#environment-variables)
6. [Smoke tests](#smoke-tests)
7. [Resetting the database](#resetting-the-database)
8. [Troubleshooting](#troubleshooting)

---

## How it works

```
Upload document → Qdrant (hybrid vector store) ← Groq LLM → Answer
                       ↑                              ↑
              fastembed (local)           context chunks retrieved
              dense + BM25 sparse         by dense + BM25 hybrid search
```

- **Ingest:** documents are chunked, embedded locally (no API cost), and stored in Qdrant with `user_id` and `visibility` (`private` / `public`) metadata.
- **Query:** your question is embedded the same way, hybrid search retrieves the most relevant chunks, and Groq streams a grounded answer.
- **Access control:** queries are filtered — you see your own documents plus all public ones.
- **Async pipeline:** ingestion and query run through Inngest for full step-by-step observability and retry support.

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | **3.12** | Required — 3.14 crashes Rust ML extensions |
| [uv](https://github.com/astral-sh/uv) | latest | `pip install uv` |
| Docker Desktop | latest | [docker.com](https://www.docker.com/products/docker-desktop/) |
| Node.js | 18+ | [nodejs.org](https://nodejs.org/) — for Inngest CLI |
| Groq API key | — | Free at [console.groq.com](https://console.groq.com) |

---

## Quick start

### 1. Clone and set up

```cmd
git clone https://github.com/micheltsarasoa/ragapp.git
cd ragapp\apps\backend
uv python install 3.12
uv pip install -r requirements.txt
```

### 2. Configure environment

Create a `.env` file at the **repo root** (`ragapp\.env`):

```env
GROQ_API_KEY=your_groq_api_key_here
```

### 3. Download embedding models (one-time)

```cmd
cd apps\backend
uv run python download_models.py
```

### 4. Start services

**Terminal 1 — Qdrant**
```cmd
docker run -d --name qdrantRagDb -p 6333:6333 -v "%cd%\qdrant_storage:/qdrant/storage" qdrant/qdrant
```

**Terminal 2 — FastAPI backend**
```cmd
cd apps\backend
uv run uvicorn app.main:app
```

**Terminal 3 — Inngest dev server**
```cmd
npx inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest --no-discovery
```

Open http://localhost:8000/docs to explore the API.

---

## Project structure

```
ragapp/
├── apps/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── core/            # config, db, data_loader, llm, vector_db
│   │   │   ├── inngest_functions/  # ingest_pdf, query_pdf, client
│   │   │   ├── models/          # Pydantic models
│   │   │   ├── routes/          # auth, documents, llm_config, query
│   │   │   └── main.py          # FastAPI app factory
│   │   ├── download_models.py   # one-time model pre-download
│   │   ├── smoke_test.py        # 8-check API smoke test
│   │   ├── requirements.txt
│   │   └── .python-version      # pins Python 3.12
│   └── frontend/                # React/Vite (in progress)
├── docs/
│   ├── setup.md                 # detailed setup guide
│   ├── testing.md               # smoke test reference
│   └── MIGRATION_PLAN.md        # monorepo migration progress
├── docker-compose.yml
├── pnpm-workspace.yaml
└── .env                         # GROQ_API_KEY (not committed)
```

---

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Yes | — | Groq API key for LLM inference |
| `LLM_MODEL` | No | `llama3-8b-8192` | Model name (any OpenAI-compatible) |
| `LLM_BASE_URL` | No | `https://api.groq.com/openai/v1` | LLM endpoint (Groq, Ollama, custom) |
| `QDRANT_URL` | No | `http://localhost:6333` | Qdrant server URL |
| `UPLOAD_DIR` | No | `uploads` | Temporary file upload directory |

---

## Smoke tests

With uvicorn running, from `apps\backend`:

```cmd
uv run python smoke_test.py
```

Covers 8 checks: LLM config, auth identity, document list, upload, visibility update, delete, and Inngest endpoint. Exit code `0` = all pass. See `docs/testing.md` for details.

---

## Resetting the database

```cmd
docker stop qdrantRagDb
docker rm qdrantRagDb
rmdir /s /q qdrant_storage
del apps\backend\ragapp.db
```

---

## Troubleshooting

### uvicorn crashes silently on startup

**Cause:** venv is using Python 3.14 (system default). Rust-based ML extensions segfault on 3.14.

**Fix:** rebuild the venv with Python 3.12:

```cmd
cd apps\backend
rmdir /s /q .venv
uv python install 3.12
uv venv --python 3.12
uv pip install -r requirements.txt
```

---

### `NoSuchFile: model_optimized.onnx` on startup

**Cause:** model download was interrupted, leaving a corrupt cache.

**Fix:** clear the cache and re-download:

```cmd
rmdir /s /q apps\backend\.fastembed_cache
cd apps\backend
uv run python download_models.py
```
