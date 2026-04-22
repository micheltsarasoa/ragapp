"""Auth route: POST /api/auth/identity — resolve or generate a user identity."""

import hashlib
import uuid

from fastapi import APIRouter

from app.models.auth import IdentityRequest, IdentityResponse

router = APIRouter()


def _derive_user_id(key: str) -> str:
    """Derive a deterministic 32-char hex user_id from an access key."""
    return hashlib.sha256(key.encode()).hexdigest()[:32]


@router.post("/api/auth/identity", response_model=IdentityResponse)
def resolve_identity(body: IdentityRequest) -> IdentityResponse:
    """Resolve or generate a user identity from an access key.

    Args:
        body: Optional access_key. If absent or empty, a new key is generated.

    Returns:
        IdentityResponse with user_id, access_key, and is_new flag.
    """
    if not body.access_key or not body.access_key.strip():
        access_key = uuid.uuid4().hex[:8].upper()
        is_new = True
    else:
        access_key = body.access_key.strip().upper()
        is_new = False

    user_id = _derive_user_id(access_key)

    return IdentityResponse(user_id=user_id, access_key=access_key, is_new=is_new)
