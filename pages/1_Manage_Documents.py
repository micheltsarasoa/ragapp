"""Document management page — list, toggle visibility, and delete documents."""

import uuid

import streamlit as st

import db
from vector_db import QdrantStorage

st.set_page_config(page_title="Manage Documents", page_icon="🗂️", layout="wide")

# Reuse the same session user_id as the main page
if "user_id" not in st.session_state:
    st.session_state["user_id"] = str(uuid.uuid4())

USER_ID: str = st.session_state["user_id"]

db.init_db()

st.title("Document Management")
st.caption(f"Your session ID: `{USER_ID}`")
st.markdown("You can see your own documents and all public documents.")

# ---------------------------------------------------------------------------
# Load documents
# ---------------------------------------------------------------------------

docs = db.list_documents(user_id=USER_ID)

if not docs:
    st.info("No documents found. Upload one from the main page.")
    st.stop()

# ---------------------------------------------------------------------------
# Render table with actions
# ---------------------------------------------------------------------------

for row in docs:
    source_id = row["source_id"]
    owner = row["user_id"]
    visibility = row["visibility"]
    ingested_at = row["ingested_at"][:19].replace("T", " ")  # trim microseconds
    chunk_count = row["chunk_count"]
    is_owner = owner == USER_ID

    with st.container(border=True):
        col_info, col_vis, col_del = st.columns([4, 2, 1])

        with col_info:
            badge = "🟢 public" if visibility == "public" else "🔒 private"
            st.markdown(f"**{source_id}**  {badge}")
            st.caption(f"{chunk_count} chunks · ingested {ingested_at}")
            if not is_owner:
                st.caption(f"Owned by another user")

        with col_vis:
            if is_owner:
                new_vis = "public" if visibility == "private" else "private"
                label = f"Make {'public' if visibility == 'private' else 'private'}"
                if st.button(label, key=f"vis_{source_id}"):
                    db.update_visibility(source_id, new_vis)
                    # Update the payload flag in Qdrant too
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
