import asyncio
import json
import os
import time
from pathlib import Path

import requests
import streamlit as st
import inngest
from dotenv import load_dotenv

from styles import inject_css, render_sidebar
from auth import resolve_identity

load_dotenv()

st.set_page_config(page_title="RAG Assistant", page_icon="⚡", layout="centered")
inject_css()

# ---------------------------------------------------------------------------
# Persistent identity — derived from a user-held access key
# ---------------------------------------------------------------------------
USER_ID, ACCESS_KEY, IS_NEW = resolve_identity()
render_sidebar(USER_ID, ACCESS_KEY, IS_NEW)

# ---------------------------------------------------------------------------
# Helpers (logic unchanged)
# ---------------------------------------------------------------------------

@st.cache_resource
def get_inngest_client() -> inngest.Inngest:
    return inngest.Inngest(app_id="rag_app", is_production=False)


def _api_base() -> str:
    return os.getenv("API_BASE", "http://127.0.0.1:8000")


def _inngest_api_base() -> str:
    return os.getenv("INNGEST_API_BASE", "http://127.0.0.1:8288/v1")


SUPPORTED_TYPES = ["pdf", "docx", "txt", "md"]


def save_uploaded_file(file) -> Path:
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    file_path = uploads_dir / file.name
    file_path.write_bytes(file.getbuffer())
    return file_path


async def send_ingest_event(file_path: Path, visibility: str) -> None:
    client = get_inngest_client()
    await client.send(
        inngest.Event(
            name="rag/ingest_pdf",
            data={
                "pdf_path": str(file_path.resolve()),
                "source_id": file_path.name,
                "user_id": USER_ID,
                "visibility": visibility,
            },
        )
    )


async def send_query_event(question: str, top_k: int) -> str:
    client = get_inngest_client()
    result = await client.send(
        inngest.Event(
            name="rag/query_pdf_ai",
            data={"question": question, "top_k": top_k, "user_id": USER_ID},
        )
    )
    return result[0]


def fetch_runs(event_id: str) -> list[dict]:
    url = f"{_inngest_api_base()}/events/{event_id}/runs"
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json().get("data", [])


def wait_for_run_output(event_id: str, timeout_s: float = 120.0) -> dict:
    start = time.time()
    last_status = None
    while True:
        runs = fetch_runs(event_id)
        if runs:
            run = runs[0]
            status = run.get("status")
            last_status = status or last_status
            if status in ("Completed", "Succeeded", "Success", "Finished"):
                return run.get("output") or {}
            if status in ("Failed", "Cancelled"):
                raise RuntimeError(f"Function run {status}")
        if time.time() - start > timeout_s:
            raise TimeoutError(f"Timed out waiting (last status: {last_status})")
        time.sleep(0.5)


def _token_stream(question: str, top_k: int):
    """Yield text tokens from the streaming endpoint; store metadata in session state."""
    url = f"{_api_base()}/api/stream_query"
    params = {"question": question, "top_k": top_k, "user_id": USER_ID}
    with requests.get(url, params=params, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        for raw_line in resp.iter_lines():
            if not raw_line:
                continue
            msg = json.loads(raw_line)
            if msg["type"] == "token":
                yield msg["content"]
            elif msg["type"] == "done":
                st.session_state["stream_meta"] = {
                    "sources": msg.get("sources", []),
                    "scores": msg.get("scores", []),
                }


def _render_sources(sources: list, scores: list) -> None:
    if not sources:
        return
    st.markdown("<p style='font-size:0.8rem;color:#6b7280;margin:0.75rem 0 0.3rem'>Sources</p>", unsafe_allow_html=True)
    badges = "".join(
        f'<span class="source-badge">{src}'
        + (f'<span class="score">{scores[i]:.3f}</span>' if i < len(scores) else "")
        + "</span>"
        for i, src in enumerate(sources)
    )
    st.markdown(f'<div class="sources-row">{badges}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

tab_upload, tab_ask = st.tabs(["📤  Upload", "💬  Ask"])

# ── Upload tab ──────────────────────────────────────────────────────────────
with tab_upload:
    st.markdown('<p class="hero-title">Upload a Document</p>', unsafe_allow_html=True)
    st.markdown(
        "<p style='color:#6b7280;font-size:0.85rem;margin-bottom:1.25rem'>"
        "Supports PDF, DOCX, TXT and Markdown files.</p>",
        unsafe_allow_html=True,
    )

    col_up, col_info = st.columns([3, 2], gap="large")

    with col_up:
        uploaded = st.file_uploader(
            "Drop your file here",
            type=SUPPORTED_TYPES,
            accept_multiple_files=False,
            label_visibility="collapsed",
        )
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        visibility = st.radio("Visibility", ["private", "public"], horizontal=True)

        if uploaded is not None:
            with st.spinner("Saving and triggering ingestion…"):
                path = save_uploaded_file(uploaded)
                asyncio.run(send_ingest_event(path, visibility))
                time.sleep(0.3)
            st.success(f"Triggered ingestion for **{path.name}** ({visibility})")
            st.caption("Processing runs in the background. Switch to the Ask tab once ready.")

    with col_info:
        st.markdown(
            """
            <div class="info-card">
                <div class="info-title">How it works</div>
                <ol>
                    <li>Choose a file and upload it</li>
                    <li>Select visibility</li>
                    <li>Wait for ingestion to complete</li>
                    <li>Switch to the Ask tab</li>
                    <li>Ask anything about the document</li>
                </ol>
                <div class="info-footer">
                    Supported&nbsp;·&nbsp;PDF &nbsp;DOCX &nbsp;TXT &nbsp;MD
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ── Ask tab ─────────────────────────────────────────────────────────────────
with tab_ask:
    st.markdown('<p class="hero-title">Ask a Question</p>', unsafe_allow_html=True)
    st.markdown(
        "<p style='color:#6b7280;font-size:0.85rem;margin-bottom:1.25rem'>"
        "Your question is answered using only the content of your documents.</p>",
        unsafe_allow_html=True,
    )

    with st.form("rag_query_form"):
        question = st.text_input(
            "question",
            placeholder="What does this document say about…?",
            label_visibility="collapsed",
        )

        with st.expander("⚙️  Advanced options"):
            col_k, col_s = st.columns([3, 2])
            with col_k:
                top_k = st.number_input(
                    "Chunks to retrieve", min_value=1, max_value=20, value=5, step=1
                )
            with col_s:
                use_stream = st.checkbox("Stream answer", value=True)

        submitted = st.form_submit_button("Ask", type="primary", use_container_width=True)

if submitted and question.strip():
    if use_stream:
        st.markdown(
            "<p style='font-weight:600;font-size:0.95rem;margin-bottom:0.5rem'>Answer</p>",
            unsafe_allow_html=True,
        )
        st.session_state["stream_meta"] = {}
        st.write_stream(_token_stream(question.strip(), int(top_k)))
        meta = st.session_state.get("stream_meta", {})
        _render_sources(meta.get("sources", []), meta.get("scores", []))
    else:
        with st.spinner("Generating answer…"):
            event_id = asyncio.run(send_query_event(question.strip(), int(top_k)))
            output = wait_for_run_output(event_id)
        answer = output.get("answer") or "(No answer)"
        st.markdown(
            f'<div class="answer-card">{answer}</div>',
            unsafe_allow_html=True,
        )
        _render_sources(output.get("sources", []), output.get("scores", []))
