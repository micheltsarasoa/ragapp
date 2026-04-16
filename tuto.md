# RAG App — Tutorial

Based on: https://www.youtube.com/watch?v=AUQJ9eeP-Ls

A Retrieval-Augmented Generation app that lets you upload documents and ask questions about them. Built with FastAPI, Inngest, Qdrant, and Streamlit.

---

## 1. Install dependencies

```bash
uv init .
uv add fastapi inngest llama-index-core llama-index-readers-file python-dotenv qdrant-client uvicorn streamlit openai fastembed docx2txt
```

> **Note:** `fastembed` downloads embedding model weights on first run (~130 MB). No OpenAI key required for embeddings.

---

## 2. Environment variables

Create a `.env` file at the root:

```env
GROQ_API_KEY=your_groq_api_key_here   # LLM inference (free tier available at console.groq.com)
LLM_MODEL=llama3-8b-8192              # optional, this is the default
API_BASE=http://127.0.0.1:8000        # optional, used by Streamlit for streaming
```

> **Tip:** Get a free Groq API key at https://console.groq.com. Groq is significantly faster and cheaper than OpenAI for inference.

---

## 3. Run the vector database (Qdrant)

Start Qdrant locally via Docker. Data is persisted to `./qdrant_storage`:

```bash
docker run -d \
  --name qdrantRagDb \
  -p 6333:6333 \
  -v "$(pwd)/qdrant_storage:/qdrant/storage" \
  qdrant/qdrant
```

---

## 4. Run the FastAPI backend

```bash
uv run uvicorn main:app
```

Available at: http://localhost:8000
Streaming query endpoint: http://localhost:8000/api/stream_query

---

## 5. Run the Inngest dev server

```bash
npx inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest --no-discovery
```

Available at: http://localhost:8288

---

## 6. Run the Streamlit frontend

```bash
uv run streamlit run streamlit_app.py
```

Available at: http://localhost:8501
Document management page: http://localhost:8501/Manage_Documents

---

## How it works

### Ingest a document
1. Upload a PDF, DOCX, TXT, or MD file in the Streamlit UI.
2. Choose visibility: **private** (only you) or **public** (all users).
3. A `rag/ingest_pdf` event is sent to Inngest.
4. The backend:
   - Chunks the document (~1000 chars, 200 overlap)
   - Embeds each chunk: dense (`BAAI/bge-small-en-v1.5`, 384-dim) + sparse (BM25)
   - Deletes any previous vectors for this source (dedup)
   - Stores vectors + metadata (`user_id`, `visibility`) in Qdrant
   - Records metadata in `ragapp.db` (SQLite)

### Ask a question
1. Type a question and choose **streaming** (real-time tokens) or **Inngest** (observable).
2. The backend:
   - Embeds the question (same models)
   - Runs hybrid search: dense cosine + BM25, fused with RRF
   - Filters results by access: your documents + public documents
   - Passes top-k chunks as context to Groq LLM
   - Returns answer + source document names + relevance scores

### Manage documents
Visit the **Manage Documents** page (sidebar) to:
- See all your documents and public documents
- Toggle a document between private ↔ public
- Delete a document (removes from Qdrant and SQLite)

---

## Docker (all services)

```bash
docker compose up --build
```

> The Inngest dev server is not included in Docker Compose — run it on the host.
> For production deployment: https://www.inngest.com/docs/deploy

---

## Test the ingest function manually (Inngest UI)

In the Inngest dev UI (http://localhost:8288), trigger `rag/ingest_pdf`:

```json
{
  "data": {
    "pdf_path": "/absolute/path/to/your/document.pdf",
    "source_id": "my-document.pdf",
    "user_id": "test-user",
    "visibility": "public"
  }
}
```

---

## Rate limits (configured)

| Function | Limit |
|----------|-------|
| Ingest | Throttle: 2 req/min; Rate limit: 1 per `source_id` per 4h |
| Query | Rate limit: 10 req/min per `user_id` |

---

## Resetting the vector database

```bash
docker stop qdrantRagDb && docker rm qdrantRagDb
rm -rf qdrant_storage ragapp.db
```

> **Required after upgrading** from the original version — the collection schema changed (hybrid vectors).

---

## See also

- `docs/architecture.md` — system diagram and config reference
- `docs/setup.md` — detailed setup guide
- `docs/access-control.md` — public/private document design
- `docs/improvements.md` — improvement history
