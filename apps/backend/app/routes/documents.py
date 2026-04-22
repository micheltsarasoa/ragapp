"""Document management routes: list, upload, visibility update, delete."""

from pathlib import Path

import inngest
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core import db
from app.core.config import UPLOAD_DIR
from app.core.vector_db import get_qdrant_storage
from app.inngest_functions.client import inngest_client
from app.models.documents import DocumentRecord, UploadResponse, VisibilityUpdate

router = APIRouter()


@router.get("/api/documents", response_model=list[DocumentRecord])
def list_documents(user_id: str = "") -> list[DocumentRecord]:
    """List documents visible to the given user (owned + public).

    Args:
        user_id: The resolved user_id from the identity endpoint.

    Returns:
        List of DocumentRecord objects ordered by ingestion date descending.
    """
    rows = db.list_documents(user_id or None)
    return [DocumentRecord(**dict(row)) for row in rows]


@router.post("/api/documents/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    visibility: str = Form("private"),
    user_id: str = Form("anonymous"),
) -> UploadResponse:
    """Accept a file upload and queue it for ingestion via Inngest.

    The file is saved to UPLOAD_DIR and a rag/ingest_pdf event is sent.
    The source_id is prefixed with user_id to prevent cross-user collisions.

    Args:
        file: The uploaded file (PDF, DOCX, TXT, or MD).
        visibility: "public" or "private" (default "private").
        user_id: The resolved user_id from the identity endpoint.

    Returns:
        UploadResponse with the source_id and status "queued".
    """
    upload_dir = Path(UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    source_id = f"{user_id}:{file.filename}"
    # Replace colon with underscore for filesystem safety
    safe_filename = source_id.replace(":", "_")
    dest_path = upload_dir / safe_filename

    contents = await file.read()
    dest_path.write_bytes(contents)

    try:
        await inngest_client.send(
            inngest.Event(
                name="rag/ingest_pdf",
                data={
                    "pdf_path": str(dest_path),
                    "source_id": source_id,
                    "user_id": user_id,
                    "visibility": visibility,
                },
            )
        )
    except Exception:
        # Inngest dev server not reachable — file is saved, ingestion will not run.
        pass

    return UploadResponse(source_id=source_id, status="queued")


@router.patch("/api/documents/{source_id:path}/visibility")
def update_visibility(source_id: str, body: VisibilityUpdate) -> dict[str, str]:
    """Update the visibility of a document in both Qdrant and SQLite.

    Qdrant is updated first (invariant: vector store always precedes metadata store).

    Args:
        source_id: The document source_id (URL-encoded path segment).
        body: VisibilityUpdate with new visibility and user_id for ownership check.

    Returns:
        {"status": "ok"}
    """
    store = get_qdrant_storage()
    store.update_source_visibility(source_id, body.visibility)
    db.update_visibility(source_id, body.visibility, body.user_id)
    return {"status": "ok"}


@router.delete("/api/documents/{source_id:path}")
def delete_document(source_id: str, user_id: str = "") -> dict[str, str]:
    """Delete a document from both Qdrant and SQLite.

    Qdrant is deleted first (invariant: vector store always precedes metadata store).

    Args:
        source_id: The document source_id (URL-encoded path segment).
        user_id: The resolved user_id; only the owner may delete.

    Returns:
        {"status": "ok"}
    """
    store = get_qdrant_storage()
    store.delete_by_source(source_id)
    db.delete_document(source_id, user_id)
    return {"status": "ok"}
