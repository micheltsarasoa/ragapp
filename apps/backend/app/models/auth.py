"""Pydantic models for the auth/identity endpoint."""

from pydantic import BaseModel


class IdentityRequest(BaseModel):
    access_key: str | None = None


class IdentityResponse(BaseModel):
    user_id: str
    access_key: str
    is_new: bool
