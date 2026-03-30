import asyncio
import json
import os
import time
import uuid
from pathlib import Path

import requests
import streamlit as st
import inngest
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="RAG App", page_icon="📄", layout="centered")

# ---------------------------------------------------------------------------
# Session identity — one stable UUID per browser session
# ---------------------------------------------------------------------------
if "user_id" not in st.session_state:
    st.session_state["user_id"] = str(uuid.uuid4())

USER_ID: str = st.session_state["user_id"]


# ---------------------------------------------------------------------------
# Helpers
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
    """Generator that yields text tokens from the streaming endpoint.

    Stores sources and scores in st.session_state['stream_meta'] when done.
    """
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


# ---------------------------------------------------------------------------
# UI: Upload
# ---------------------------------------------------------------------------

st.title("Upload a Document")
uploaded = st.file_uploader(
    "Choose a file", type=SUPPORTED_TYPES, accept_multiple_files=False
)
visibility = st.radio("Visibility", ["private", "public"], horizontal=True)

if uploaded is not None:
    with st.spinner("Saving and triggering ingestion..."):
        path = save_uploaded_file(uploaded)
        asyncio.run(send_ingest_event(path, visibility))
        time.sleep(0.3)
    st.success(f"Triggered ingestion for **{path.name}** ({visibility})")
    st.caption("Processing happens in the background. Ask a question once it finishes.")

st.divider()

# ---------------------------------------------------------------------------
# UI: Query
# ---------------------------------------------------------------------------

st.title("Ask a Question")

with st.form("rag_query_form"):
    question = st.text_input("Your question")
    col1, col2 = st.columns([3, 1])
    with col1:
        top_k = st.number_input(
            "Chunks to retrieve", min_value=1, max_value=20, value=5, step=1
        )
    with col2:
        use_stream = st.checkbox("Stream answer", value=True)
    submitted = st.form_submit_button("Ask")

if submitted and question.strip():
    if use_stream:
        # Streaming mode: direct call to FastAPI, real-time token output
        st.subheader("Answer")
        st.session_state["stream_meta"] = {}
        st.write_stream(_token_stream(question.strip(), int(top_k)))
        meta = st.session_state.get("stream_meta", {})
        sources = meta.get("sources", [])
        scores = meta.get("scores", [])
    else:
        # Inngest mode: observable, non-streaming
        with st.spinner("Generating answer via Inngest..."):
            event_id = asyncio.run(send_query_event(question.strip(), int(top_k)))
            output = wait_for_run_output(event_id)
        st.subheader("Answer")
        st.write(output.get("answer") or "(No answer)")
        sources = output.get("sources", [])
        scores = output.get("scores", [])

    if submitted and question.strip():
        if sources:
            st.caption("Sources")
            for i, src in enumerate(sources):
                score_label = f"  (score: {scores[i]:.4f})" if i < len(scores) else ""
                st.write(f"- {src}{score_label}")
