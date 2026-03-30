# Architecture

## Overview

```
┌─────────────────────────────────────────────────────────┐
│                  Streamlit (port 8501)                  │
│              Upload PDF  |  Ask a question              │
└────────────────────┬────────────────┬───────────────────┘
                     │                │
              rag/ingest_pdf    rag/query_pdf_ai
                     │                │
┌────────────────────▼────────────────▼───────────────────┐
│               Inngest Dev Server (port 8288)            │
│               Event queue + function runner             │
└────────────────────┬────────────────────────────────────┘
                     │  HTTP (Inngest → FastAPI)
┌────────────────────▼────────────────────────────────────┐
│                 FastAPI (port 8000)                     │
│           /api/inngest  (Inngest handler)               │
│                                                         │
│  rag_ingest_pdf function:                               │
│    Step 1: load_and_chunk_pdf()  ← LlamaIndex PDFReader │
│    Step 2: embed_texts()          ← OpenAI embeddings   │
│    Step 3: QdrantStorage.upsert()                       │
│                                                         │
│  rag_query_pdf_ai function:                             │
│    Step 1: embed_texts(question)                        │
│    Step 2: QdrantStorage.search()                       │
│    Step 3: ctx.step.ai.infer()    ← OpenAI gpt-4o-mini  │
└───────────────────────────┬─────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
┌───────▼────────┐                   ┌──────────▼──────────┐
│ Qdrant (6333)  │                   │   OpenAI API        │
│ Vector store   │                   │  - text-embedding   │
│ collection:    │                   │    -3-large (3072d) │
│   "docs"       │                   │  - gpt-4o-mini      │
└────────────────┘                   └─────────────────────┘
```

---

## Key components

| File | Role |
|------|------|
| `main.py` | FastAPI app + Inngest function definitions |
| `streamlit_app.py` | Web UI for upload and querying |
| `data_loader.py` | PDF reading and text chunking + OpenAI embeddings |
| `vector_db.py` | Qdrant client wrapper (upsert + search) |
| `custom_types.py` | Pydantic models shared between steps |

---

## Data flow: Ingestion

```
PDF file (local disk)
  → PDFReader (LlamaIndex)          # extract text per page
  → SentenceSplitter                # 1000-char chunks, 200-char overlap
  → OpenAI text-embedding-3-large   # 3072-dim float vectors
  → UUID v5 per chunk               # deterministic, idempotent IDs
  → Qdrant upsert                   # payload: {source, text}
```

## Data flow: Query

```
User question (string)
  → OpenAI text-embedding-3-large   # same model as ingestion
  → Qdrant cosine similarity search # top-k chunks
  → Prompt construction             # context + question
  → gpt-4o-mini (temp=0.2)          # answer grounded in context
  → Return answer + sources
```

---

## Configuration reference

| Parameter | Value | Location |
|-----------|-------|----------|
| Embedding model | `text-embedding-3-large` | `data_loader.py` |
| Embedding dimensions | 3072 | `data_loader.py`, `vector_db.py` |
| LLM model | `gpt-4o-mini` | `main.py` |
| LLM temperature | 0.2 | `main.py` |
| Chunk size | 1000 chars | `data_loader.py` |
| Chunk overlap | 200 chars | `data_loader.py` |
| Qdrant URL | `http://localhost:6333` | `vector_db.py` |
| Qdrant collection | `docs` | `vector_db.py` |
| Inngest app ID | `rag_app` | `main.py` |
| Default top-k | 5 | `main.py`, `streamlit_app.py` |
| Ingest throttle | 2 req/min | `main.py` |
| Ingest rate limit | 1 per `source_id` / 4h | `main.py` |
