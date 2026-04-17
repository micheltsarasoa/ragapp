"""Document management page — list, toggle visibility, and delete documents."""

import html as _html
import streamlit as st
from datetime import datetime

import db
from vector_db import get_qdrant_storage
from styles import inject_css, render_sidebar
from auth import resolve_identity

st.set_page_config(page_title="Manage Documents", page_icon="🗂️", layout="wide")
inject_css()

USER_ID, ACCESS_KEY, IS_NEW = resolve_identity()
render_sidebar(USER_ID, ACCESS_KEY, IS_NEW)

# ---------------------------------------------------------------------------
# One-time DB initialisation (runs once per process, not on every rerun)
# ---------------------------------------------------------------------------


@st.cache_resource
def _init_db() -> None:
    """Initialise the SQLite schema exactly once per process lifetime."""
    db.init_db()


_init_db()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fmt_ingested(value: object) -> str:
    """Return a human-readable timestamp string from an ISO-8601 value.

    Args:
        value: Raw ``ingested_at`` column value; may be ``None`` or any string.

    Returns:
        Formatted ``YYYY-MM-DD HH:MM:SS`` string, or ``"unknown"`` on failure.
    """
    if value is None:
        return "unknown"
    try:
        return datetime.fromisoformat(str(value)).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return str(value)


# ---------------------------------------------------------------------------
# Load documents
# ---------------------------------------------------------------------------

docs = db.list_documents(user_id=USER_ID)

total_docs = len(docs)
my_docs = sum(1 for d in docs if d["user_id"] == USER_ID)
public_docs = sum(1 for d in docs if d["visibility"] == "public")

# ---------------------------------------------------------------------------
# Header + stats
# ---------------------------------------------------------------------------

st.markdown('<p class="hero-title">Document Management</p>', unsafe_allow_html=True)
st.markdown(
    "<p style='color:#6b7280;font-size:0.85rem;margin-bottom:1.25rem'>"
    "Your documents and all public documents are listed here.</p>",
    unsafe_allow_html=True,
)

col_t, col_m, col_p, col_pad = st.columns([1, 1, 1, 3])
with col_t:
    st.metric("Total Visible", total_docs)
with col_m:
    st.metric("My Documents", my_docs)
with col_p:
    st.metric("Public", public_docs)

st.divider()

# ---------------------------------------------------------------------------
# Empty state
# ---------------------------------------------------------------------------

if not docs:
    st.markdown(
        '<div class="answer-card" style="text-align:center;color:#6b7280;padding:2rem">'
        "📭&nbsp; No documents yet. Upload one from the main page."
        "</div>",
        unsafe_allow_html=True,
    )
    st.stop()

# ---------------------------------------------------------------------------
# Document cards
# ---------------------------------------------------------------------------

for row in docs:
    source_id = row["source_id"]
    owner = row["user_id"]
    visibility = row["visibility"]
    ingested_at = _fmt_ingested(row["ingested_at"])
    chunk_count = row["chunk_count"]
    is_owner = owner == USER_ID

    # Escape all user-derived values before HTML interpolation (MD-H1)
    safe_source_id = _html.escape(str(source_id))
    safe_chunk_count = _html.escape(str(chunk_count))
    safe_ingested_at = _html.escape(ingested_at)

    if visibility == "public":
        badge_html = '<span class="vis-badge-public">● public</span>'
    else:
        badge_html = '<span class="vis-badge-private">◆ private</span>'

    owner_badge = "" if is_owner else '<span class="vis-badge-other">shared</span>'

    col_info, col_vis, col_del = st.columns([6, 2, 1], gap="small")

    with col_info:
        st.markdown(
            f"""
            <div class="doc-card">
                <div class="doc-name">{safe_source_id}</div>
                <div class="doc-meta">
                    {safe_chunk_count} chunks &nbsp;·&nbsp; {safe_ingested_at}
                    &nbsp; {badge_html} {owner_badge}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # -----------------------------------------------------------------------
    # Visibility toggle (MD-H2: Qdrant first, SQLite only on success)
    # -----------------------------------------------------------------------
    with col_vis:
        if is_owner:
            new_vis = "public" if visibility == "private" else "private"
            label = f"Make {'public' if visibility == 'private' else 'private'}"
            if st.button(label, key=f"vis_{source_id}", use_container_width=True):
                try:
                    get_qdrant_storage().update_source_visibility(source_id, new_vis)
                except Exception as e:
                    st.error(f"Visibility update failed (Qdrant): {e}")
                else:
                    db.update_visibility(source_id, new_vis, USER_ID)
                    st.rerun()

    # -----------------------------------------------------------------------
    # Delete with two-click confirmation (MD-M2)
    # Qdrant first, SQLite only on success (MD-H2)
    # -----------------------------------------------------------------------
    with col_del:
        if is_owner:
            confirm_key = f"confirm_del_{source_id}"

            if st.session_state.get(confirm_key):
                # Second-click confirmation row
                st.warning("Delete?")
                yes_col, cancel_col = st.columns(2)

                with yes_col:
                    if st.button("Yes", key=f"del_yes_{source_id}", use_container_width=True):
                        try:
                            get_qdrant_storage().delete_by_source(source_id)
                        except Exception as e:
                            st.error(f"Deletion failed (Qdrant): {e}")
                            st.session_state.pop(confirm_key, None)
                        else:
                            db.delete_document(source_id, USER_ID)
                            st.session_state.pop(confirm_key, None)
                            st.rerun()

                with cancel_col:
                    if st.button("Cancel", key=f"del_cancel_{source_id}", use_container_width=True):
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
            else:
                # First click — arm the confirmation
                if st.button("🗑️", key=f"del_{source_id}", help="Delete document"):
                    st.session_state[confirm_key] = True
                    st.rerun()

    st.markdown("<div style='height:0.15rem'></div>", unsafe_allow_html=True)
