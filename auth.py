"""
User identity resolution via a persistent access key.

How it works:
  - On first visit: a short random key is generated (e.g. "A3F7B2C1").
  - The key is written to the URL as ?key=A3F7B2C1. Bookmarking that URL
    or copying the key is enough to regain access to private documents.
  - The user_id stored in Qdrant / SQLite is a SHA-256 hash of the key,
    so the same key always maps to the same identity.
  - Users can switch to a different key (e.g. one from a previous session)
    via the sidebar form.
"""

import hashlib
import uuid

import streamlit as st


def resolve_identity() -> tuple[str, str, bool]:
    """Resolve the current user's identity from session state or URL params.

    Returns:
        user_id    — 32-char hex string used in Qdrant / SQLite
        access_key — human-readable key the user sees and copies
        is_new     — True when the key was just generated (show save warning)
    """
    if "user_id" in st.session_state:
        return (
            st.session_state["user_id"],
            st.session_state["access_key"],
            st.session_state.get("is_new_key", False),
        )

    # Try query param first (?key=...)
    raw = st.query_params.get("key", "").strip().upper()
    is_new = False

    if not raw:
        raw = uuid.uuid4().hex[:8].upper()   # e.g. "A3F7B2C1"
        is_new = True

    user_id = _derive_user_id(raw)

    st.session_state["user_id"]    = user_id
    st.session_state["access_key"] = raw
    st.session_state["is_new_key"] = is_new

    # Persist in URL so the page can be bookmarked
    st.query_params["key"] = raw

    return user_id, raw, is_new


def apply_key(raw_key: str) -> None:
    """Switch to a different access key and update the URL."""
    key = raw_key.strip().upper()
    if not key:
        return
    st.session_state["user_id"]    = _derive_user_id(key)
    st.session_state["access_key"] = key
    st.session_state["is_new_key"] = False
    st.query_params["key"] = key


def _derive_user_id(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:32]
