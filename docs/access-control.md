# Document Access Control

This document describes how to design public vs. private document access in the RAG app.

---

## Current state

All documents are stored in a single Qdrant collection (`docs`) without any ownership or visibility information. Every query searches all documents regardless of who uploaded them.

---

## Proposed design

The simplest approach is **metadata-based filtering** — add `user_id` and `visibility` fields to every Qdrant point payload, then apply filters at query time.

### Payload schema (extended)

```json
{
  "source": "my-document.pdf",
  "text": "...",
  "user_id": "user_abc123",
  "visibility": "private"
}
```

`visibility` is either `"public"` or `"private"`.

---

## Ingestion changes

When uploading, the frontend sends `user_id` and `visibility` alongside the file:

```python
# Inngest event data
{
  "pdf_path": "/uploads/document.pdf",
  "source_id": "document.pdf",
  "user_id": "user_abc123",
  "visibility": "private"   # or "public"
}
```

In `main.py`, the payload stored in Qdrant becomes:

```python
payloads = [
    {
        "source": source_id,
        "text": chunks[i],
        "user_id": user_id,
        "visibility": visibility,
    }
    for i in range(len(chunks))
]
```

---

## Query changes

At query time, the search must filter to only return:
- documents with `visibility == "public"`, **OR**
- documents owned by the requesting user (`user_id == current_user`)

Using the Qdrant filter API:

```python
from qdrant_client.models import Filter, Should, FieldCondition, MatchValue

def build_access_filter(user_id: str) -> Filter:
    return Filter(
        should=[
            FieldCondition(key="visibility", match=MatchValue(value="public")),
            FieldCondition(key="user_id",    match=MatchValue(value=user_id)),
        ]
    )
```

Pass this filter into `QdrantStorage.search()`:

```python
results = self.client.search(
    collection_name=self.collection,
    query_vector=query_vector,
    query_filter=build_access_filter(user_id),
    with_payload=True,
    limit=top_k,
)
```

---

## User identity

The app currently has no authentication. To add one, the easiest options are:

| Option | Complexity | Notes |
|--------|-----------|-------|
| Streamlit `st.session_state` UUID | Low | Not persistent, suitable for demos |
| [Streamlit-Authenticator](https://github.com/mkhorasani/Streamlit-Authenticator) | Medium | Simple login form, YAML-based config |
| OAuth (Google, GitHub via Auth0) | High | Recommended for production |

For a quick demo, generate a random `user_id` per browser session and store it in `st.session_state`. The access control logic in Qdrant remains the same regardless of the auth method.

---

## Making a document public (admin flow)

Add a management UI (or a separate admin page) where a user or admin can toggle visibility:

```python
# Update a document's visibility in Qdrant
client.set_payload(
    collection_name="docs",
    payload={"visibility": "public"},
    points=Filter(
        must=[FieldCondition(key="source", match=MatchValue(value="document.pdf"))]
    ),
)
```

---

## Summary of changes required

1. **`streamlit_app.py`** — add user identity (session UUID or auth), pass `user_id` + `visibility` in ingest event
2. **`main.py`** — include `user_id` and `visibility` in Qdrant payloads; pass `user_id` in query event
3. **`vector_db.py`** — add optional `query_filter` parameter to `search()`
4. **`custom_types.py`** — update `RAGChunkAndSrc` to include `user_id` and `visibility`
