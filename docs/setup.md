# Setup Guide

## Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager
- Docker (for Qdrant)
- Node.js (for Inngest CLI)
- An OpenAI API key

---

## Quick start

### 1. Install dependencies

```bash
uv init .
uv add fastapi inngest llama-index-core llama-index-readers-file \
       python-dotenv qdrant-client uvicorn streamlit openai
```

### 2. Configure environment

```bash
# .env
OPENAI_API_KEY=sk-...
```

### 3. Start all services (four terminals)

**Terminal 1 — Qdrant vector database**
```bash
docker run -d \
  --name qdrantRagDb \
  -p 6333:6333 \
  -v "$(pwd)/qdrant_storage:/qdrant/storage" \
  qdrant/qdrant
```

**Terminal 2 — FastAPI backend**
```bash
uv run uvicorn main:app
# → http://localhost:8000
```

**Terminal 3 — Inngest dev server**
```bash
npx inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest --no-discovery
# → http://localhost:8288
```

**Terminal 4 — Streamlit frontend**
```bash
uv run streamlit run streamlit_app.py
# → http://localhost:8501
```

---

## Using the app

1. Open http://localhost:8501
2. **Upload** a PDF — ingestion is triggered automatically in the background
3. Wait a few seconds, then **ask a question** about the uploaded document
4. Adjust the "chunks to retrieve" slider if the answer lacks detail

---

## Monitoring

Open the **Inngest dev UI** at http://localhost:8288 to:
- Inspect event triggers
- See step-by-step execution logs
- Replay or debug failed runs

---

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | — | OpenAI API key |
| `INNGEST_API_BASE` | No | `http://127.0.0.1:8288/v1` | Inngest API base URL |

---

## Resetting the vector database

To wipe all ingested documents and start fresh:

```bash
docker stop qdrantRagDb && docker rm qdrantRagDb
rm -rf qdrant_storage
```

Then re-run the Docker command from step 3.
