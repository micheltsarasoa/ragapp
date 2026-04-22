"""Pydantic models for document management endpoints."""

from pydantic import BaseModel


class DocumentRecord(BaseModel):
    source_id: str
    user_id: str
    visibility: str
    ingested_at: str
    chunk_count: int


class UploadResponse(BaseModel):
    source_id: str
    status: str  # "queued"


class VisibilityUpdate(BaseModel):
    visibility: str  # "public" | "private"
    user_id: str
