# RAG App — Tutorial

Based on: https://www.youtube.com/watch?v=AUQJ9eeP-Ls

A Retrieval-Augmented Generation app that lets you upload PDFs and ask questions about them. Built with FastAPI, Inngest, Qdrant, and Streamlit.

---

## 1. Initialize the project

```bash
uv init .
uv add fastapi inngest llama-index-core llama-index-readers-file python-dotenv qdrant-client uvicorn streamlit openai
```

---

## 2. Environment variables

Create a `.env` file at the root:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

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

---

## 5. Run the Inngest dev server

Inngest orchestrates the background functions. Connect it to your local FastAPI backend:

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

---

## How it works

### Ingest a PDF
1. Upload a PDF in the Streamlit UI.
2. The file is saved to `uploads/` and a `rag/ingest_pdf` event is sent to Inngest.
3. Inngest calls the FastAPI function which:
   - Chunks the PDF into ~1000-character segments (200-char overlap)
   - Embeds each chunk with OpenAI `text-embedding-3-large`
   - Stores vectors + metadata in Qdrant

### Ask a question
1. Type a question in the Streamlit UI.
2. A `rag/query_pdf_ai` event is sent to Inngest.
3. Inngest calls the FastAPI function which:
   - Embeds the question
   - Retrieves the top-k most similar chunks from Qdrant
   - Passes them as context to `gpt-4o-mini`
   - Returns the answer + source documents

---

## Test the ingest function manually (Inngest UI)

In the Inngest dev UI (http://localhost:8288), you can trigger `rag/ingest_pdf` manually:

```json
{
  "data": {
    "pdf_path": "/absolute/path/to/your/document.pdf",
    "source_id": "my-document.pdf"
  }
}
```

---

## Rate limiting (already configured)

The ingest function is protected by:
- **Throttle:** max 2 requests per minute
- **Rate limit:** max 1 ingest per `source_id` every 4 hours (prevents re-ingesting the same document)

---

## Next steps

- See `docs/` for architecture details, access control design, and improvement suggestions.
- For production deployment, refer to the [Inngest deployment docs](https://www.inngest.com/docs).
