# Suggested Improvements

Ordered by impact vs. implementation effort.

---

## High priority

### 1. Replace OpenAI embeddings with a local model
**Why:** Embedding every chunk and every query calls the OpenAI API, which adds latency and cost.
**How:** Use [fastembed](https://github.com/qdrant/fastembed) (runs locally, no API key needed):
```python
from fastembed import TextEmbedding
model = TextEmbedding("BAAI/bge-small-en-v1.5")  # 384-dim, fast
```
Adjust `EMBED_DIM` in `vector_db.py` to match the chosen model.

---

### 2. Switch LLM to Groq (faster, cheaper)
**Why:** `gpt-4o-mini` is good but Groq's hosted Llama 3 / Mixtral models are significantly faster and cheaper for inference.
**How:** The OpenAI SDK is compatible with Groq's API:
```python
from openai import OpenAI
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)
```
Change `model` to `"llama3-8b-8192"` or `"mixtral-8x7b-32768"`.

---

### 3. Add rate limiting to queries
**Why:** Currently, `rag/query_pdf_ai` has no limits — a single user can spam queries.
**How:** Add an Inngest rate limit keyed on `user_id`:
```python
rate_limit=inngest.RateLimit(
    limit=10,
    period=datetime.timedelta(minutes=1),
    key="event.data.user_id",
)
```

---

### 4. Deduplicate / re-ingest detection
**Why:** Uploading the same PDF twice ingests duplicate chunks (even with UUID v5, the old chunks stay if the document changed).
**How:** Before ingesting, delete all existing points for that `source_id`:
```python
client.delete(
    collection_name="docs",
    points_selector=Filter(
        must=[FieldCondition(key="source", match=MatchValue(value=source_id))]
    ),
)
```

---

## Medium priority

### 5. Stream the LLM response
**Why:** Users wait for the entire answer before seeing anything.
**How:** Use OpenAI streaming in a Streamlit `st.write_stream()` context. Note: this requires bypassing Inngest for the LLM call and calling OpenAI directly from the frontend or a streaming FastAPI endpoint.

---

### 6. Show chunk scores in the UI
**Why:** Transparency — users can see how confident the retrieval was.
**How:** Return `score` from Qdrant search results and display them alongside source names.

---

### 7. Support more file types
**Why:** Users may want to ingest `.docx`, `.txt`, `.md`, or web pages.
**How:** LlamaIndex has readers for all common formats. Add a type-dispatch in `data_loader.py` based on file extension.

---

### 8. Persist uploads metadata in a database
**Why:** Currently there is no record of which files were ingested, by whom, or when.
**How:** Use SQLite (via `aiosqlite`) or a lightweight hosted DB (PlanetScale, Supabase free tier) to store `{source_id, user_id, visibility, ingested_at, chunk_count}`.

---

## Low priority / polish

### 9. Dockerize the full stack
Add a `docker-compose.yml` to spin up Qdrant + FastAPI + Streamlit together:
```yaml
services:
  qdrant:
    image: qdrant/qdrant
    ports: ["6333:6333"]
    volumes: ["./qdrant_storage:/qdrant/storage"]
  api:
    build: .
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [qdrant]
  ui:
    build: .
    command: uv run streamlit run streamlit_app.py
    ports: ["8501:8501"]
    depends_on: [api]
```

### 10. Add a document management page
A second Streamlit page (using `st.navigation`) to list uploaded documents, see chunk counts, toggle visibility (public/private), and delete documents.

### 11. Implement hybrid search
Combine vector similarity with BM25 keyword search (Qdrant supports sparse vectors natively) for better retrieval on exact-match queries like names, dates, or codes.
