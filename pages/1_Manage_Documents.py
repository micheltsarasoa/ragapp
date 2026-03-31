"""Document management page — list, toggle visibility, and delete documents."""

import uuid

import streamlit as st

import db
from vector_db import QdrantStorage
from styles import inject_css, render_sidebar

st.set_page_config(page_title="Manage Documents", page_icon="🗂️", layout="wide")
inject_css()

# Reuse the same session user_id as the main page
if "user_id" not in st.session_state:
    st.session_state["user_id"] = str(uuid.uuid4())

USER_ID: str = st.session_state["user_id"]
render_sidebar(USER_ID)

db.init_db()

# ---------------------------------------------------------------------------
# Load documents
# ---------------------------------------------------------------------------

docs = db.list_documents(user_id=USER_ID)

total_docs = len(docs)
my_docs    = sum(1 for d in docs if d["user_id"] == USER_ID)
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
    source_id  = row["source_id"]
    owner      = row["user_id"]
    visibility = row["visibility"]
    ingested_at = row["ingested_at"][:19].replace("T", " ")
    chunk_count = row["chunk_count"]
    is_owner   = owner == USER_ID

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
                <div class="doc-name">{source_id}</div>
                <div class="doc-meta">
                    {chunk_count} chunks &nbsp;·&nbsp; {ingested_at}
                    &nbsp; {badge_html} {owner_badge}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_vis:
        if is_owner:
            new_vis = "public" if visibility == "private" else "private"
            label = f"Make {'public' if visibility == 'private' else 'private'}"
            if st.button(label, key=f"vis_{source_id}", use_container_width=True):
                db.update_visibility(source_id, new_vis)
                try:
                    qs = QdrantStorage()
                    from qdrant_client.models import Filter, FieldCondition, MatchValue
                    qs.client.set_payload(
                        collection_name=qs.collection,
                        payload={"visibility": new_vis},
                        points=Filter(
                            must=[FieldCondition(
                                key="source", match=MatchValue(value=source_id)
                            )]
                        ),
                    )
                except Exception as e:
                    st.warning(f"Qdrant update skipped: {e}")
                st.rerun()

    with col_del:
        if is_owner:
            if st.button("🗑️", key=f"del_{source_id}", help="Delete document"):
                try:
                    QdrantStorage().delete_by_source(source_id)
                except Exception as e:
                    st.warning(f"Qdrant deletion error: {e}")
                db.delete_document(source_id)
                st.rerun()

    st.markdown("<div style='height:0.15rem'></div>", unsafe_allow_html=True)
