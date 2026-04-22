# Setup Guide

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | **3.12** | Required — 3.14 crashes Rust ML extensions |
| [uv](https://github.com/astral-sh/uv) | latest | `pip install uv` |
| Docker Desktop | latest | For Qdrant vector database |
| Node.js | 18+ | For Inngest CLI |
| Groq API key | — | Free at [console.groq.com](https://console.groq.com) |

---

## Quick start

### 1. Pin Python and install dependencies

```cmd
cd apps\backend
uv python install 3.12
uv pip install -r requirements.txt
```

> A `.python-version` file is already committed — `uv` will always use 3.12 for this project automatically.

### 2. Configure environment

Create a `.env` file at the **repo root**:

```env
GROQ_API_KEY=your_groq_api_key_here
```

### 3. Download embedding models (one-time)

Run this once before starting the backend for the first time:

```cmd
cd apps\backend
uv run python download_models.py
```

This downloads two local models into `apps\backend\.fastembed_cache\`:
- `BAAI/bge-small-en-v1.5` — dense ONNX model (~64 MB)
- `Qdrant/bm25` — sparse BM25 stopword files (~25 KB)

Subsequent starts are instant — models are cached locally and never re-downloaded.

<details>
<summary>Manual download (if the script fails)</summary>

Place files in `apps\backend\.fastembed_cache\` following this structure:

```
models--qdrant--bge-small-en-v1.5-onnx-q\
  refs\
    main                          ← text file: 52398278842ec682c6f32300af41344b1c0b0bb2
  snapshots\
    52398278842ec682c6f32300af41344b1c0b0bb2\
      config.json
      special_tokens_map.json
      tokenizer.json
      tokenizer_config.json
      model_optimized.onnx        ← ~64 MB

models--Qdrant--bm25\
  refs\
    main                          ← text file: e499a1f8d6bec960aab5533a0941bf914e70faf9
  snapshots\
    e499a1f8d6bec960aab5533a0941bf914e70faf9\
      config.json
      arabic.txt  danish.txt  dutch.txt  english.txt  finnish.txt
      french.txt  german.txt  greek.txt  hungarian.txt  italian.txt
      norwegian.txt  portuguese.txt  romanian.txt  russian.txt
      spanish.txt  swedish.txt  turkish.txt
```

Dense model files (`snapshots\52398278842ec682c6f32300af41344b1c0b0bb2\`):

| File | URL |
|---|---|
| `config.json` | https://huggingface.co/Qdrant/bge-small-en-v1.5-onnx-Q/resolve/main/config.json |
| `special_tokens_map.json` | https://huggingface.co/Qdrant/bge-small-en-v1.5-onnx-Q/resolve/main/special_tokens_map.json |
| `tokenizer.json` | https://huggingface.co/Qdrant/bge-small-en-v1.5-onnx-Q/resolve/main/tokenizer.json |
| `tokenizer_config.json` | https://huggingface.co/Qdrant/bge-small-en-v1.5-onnx-Q/resolve/main/tokenizer_config.json |
| `model_optimized.onnx` | https://huggingface.co/Qdrant/bge-small-en-v1.5-onnx-Q/resolve/main/model_optimized.onnx |

Sparse model files (`snapshots\e499a1f8d6bec960aab5533a0941bf914e70faf9\`):

| File | URL |
|---|---|
| `config.json` | https://huggingface.co/Qdrant/bm25/resolve/main/config.json |
| `arabic.txt` | https://huggingface.co/Qdrant/bm25/resolve/main/arabic.txt |
| `danish.txt` | https://huggingface.co/Qdrant/bm25/resolve/main/danish.txt |
| `dutch.txt` | https://huggingface.co/Qdrant/bm25/resolve/main/dutch.txt |
| `english.txt` | https://huggingface.co/Qdrant/bm25/resolve/main/english.txt |
| `finnish.txt` | https://huggingface.co/Qdrant/bm25/resolve/main/finnish.txt |
| `french.txt` | https://huggingface.co/Qdrant/bm25/resolve/main/french.txt |
| `german.txt` | https://huggingface.co/Qdrant/bm25/resolve/main/german.txt |
| `greek.txt` | https://huggingface.co/Qdrant/bm25/resolve/main/greek.txt |
| `hungarian.txt` | https://huggingface.co/Qdrant/bm25/resolve/main/hungarian.txt |
| `italian.txt` | https://huggingface.co/Qdrant/bm25/resolve/main/italian.txt |
| `norwegian.txt` | https://huggingface.co/Qdrant/bm25/resolve/main/norwegian.txt |
| `portuguese.txt` | https://huggingface.co/Qdrant/bm25/resolve/main/portuguese.txt |
| `romanian.txt` | https://huggingface.co/Qdrant/bm25/resolve/main/romanian.txt |
| `russian.txt` | https://huggingface.co/Qdrant/bm25/resolve/main/russian.txt |
| `spanish.txt` | https://huggingface.co/Qdrant/bm25/resolve/main/spanish.txt |
| `swedish.txt` | https://huggingface.co/Qdrant/bm25/resolve/main/swedish.txt |
| `turkish.txt` | https://huggingface.co/Qdrant/bm25/resolve/main/turkish.txt |

</details>

### 4. Start all services

**Terminal 1 — Qdrant vector database**

```cmd
docker run -d --name qdrantRagDb -p 6333:6333 -v "%cd%\qdrant_storage:/qdrant/storage" qdrant/qdrant
```

> PowerShell: replace `%cd%` with `${PWD}`

**Terminal 2 — FastAPI backend**

```cmd
cd apps\backend
uv run uvicorn app.main:app
```

→ http://localhost:8000 · API docs at http://localhost:8000/docs

**Terminal 3 — Inngest dev server**

```cmd
npx inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest --no-discovery
```

→ http://localhost:8288

---

## Using the app

- **API docs (Swagger UI):** http://localhost:8000/docs
- **Upload a document:** `POST /api/documents/upload`
- **Ask a question:** `GET /api/stream_query?question=...&user_id=...`
- **Inngest dashboard:** http://localhost:8288 — inspect event triggers, step logs, replay failed runs

---

## Running smoke tests

With uvicorn running:

```cmd
cd apps\backend
uv run python smoke_test.py
```

See `docs/testing.md` for what each check verifies.

---

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Yes | — | Groq API key for LLM inference |
| `LLM_MODEL` | No | `llama3-8b-8192` | Model name (any Groq-compatible model) |
| `LLM_BASE_URL` | No | `https://api.groq.com/openai/v1` | OpenAI-compatible endpoint (Groq, Ollama, custom) |
| `QDRANT_URL` | No | `http://localhost:6333` | Qdrant server URL |
| `UPLOAD_DIR` | No | `uploads` | Directory for temporary uploaded files |
| `FASTEMBED_CACHE_PATH` | No | `apps\backend\.fastembed_cache` | Path to embedding model cache |

---

## Resetting the vector database

To wipe all ingested documents and start fresh:

```cmd
docker stop qdrantRagDb
docker rm qdrantRagDb
rmdir /s /q qdrant_storage
```

Then re-run the Docker command from step 4.
