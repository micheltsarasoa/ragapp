"""Shared UI helpers: CSS injection and sidebar branding."""

import streamlit as st

_CSS = """
/* ── Global ─────────────────────────────────────────────────────────────── */
*, *::before, *::after {
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    box-sizing: border-box;
}

/* Thin scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0f1117; }
::-webkit-scrollbar-thumb { background: #374151; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #6366f1; }

a { color: #818cf8 !important; text-decoration: none; }
a:hover { color: #a5b4fc !important; text-decoration: underline; }

/* ── App background ──────────────────────────────────────────────────────── */
.stApp {
    background: linear-gradient(135deg, #0f1117 0%, #111827 100%) !important;
}

/* ── Buttons ─────────────────────────────────────────────────────────────── */
[data-testid="stBaseButton-secondary"] button,
[data-testid="stBaseButton-primary"] button {
    border-radius: 8px !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}

[data-testid="stBaseButton-secondary"] button {
    background: transparent !important;
    border: 1px solid #374151 !important;
    color: #e2e8f0 !important;
}
[data-testid="stBaseButton-secondary"] button:hover {
    border-color: #6366f1 !important;
    color: #a5b4fc !important;
    background: rgba(99,102,241,0.08) !important;
    box-shadow: 0 0 0 2px rgba(99,102,241,0.2) !important;
}

[data-testid="stBaseButton-primary"] button {
    background: linear-gradient(135deg, #6366f1, #7c3aed) !important;
    border: none !important;
    color: #ffffff !important;
    box-shadow: 0 4px 15px rgba(99,102,241,0.3) !important;
}
[data-testid="stBaseButton-primary"] button:hover {
    background: linear-gradient(135deg, #4f46e5, #6d28d9) !important;
    box-shadow: 0 6px 20px rgba(99,102,241,0.45) !important;
    transform: translateY(-1px) !important;
}
[data-testid="stBaseButton-primary"] button:active {
    transform: translateY(0) !important;
}

/* ── Inputs ──────────────────────────────────────────────────────────────── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stNumberInput"] input {
    background: #1a1d27 !important;
    border: 1px solid #2d3748 !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus,
[data-testid="stNumberInput"] input:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.25) !important;
    outline: none !important;
}

/* ── File uploader ───────────────────────────────────────────────────────── */
[data-testid="stFileUploader"] {
    border: 2px dashed #374151 !important;
    border-radius: 12px !important;
    padding: 1.5rem !important;
    background: rgba(26,29,39,0.6) !important;
    transition: border-color 0.25s ease, background 0.25s ease !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: #6366f1 !important;
    background: rgba(99,102,241,0.06) !important;
}
[data-testid="stFileUploadDropzone"] {
    background: transparent !important;
}

/* ── Tabs ────────────────────────────────────────────────────────────────── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid #2d3748 !important;
    gap: 0.25rem;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    background: transparent !important;
    color: #94a3b8 !important;
    border-radius: 6px 6px 0 0 !important;
    font-weight: 500 !important;
    padding: 0.6rem 1.1rem !important;
    transition: color 0.15s ease, background 0.15s ease !important;
}
[data-testid="stTabs"] [data-baseweb="tab"]:hover {
    color: #e2e8f0 !important;
    background: rgba(99,102,241,0.06) !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    color: #a5b4fc !important;
    border-bottom: 2px solid #6366f1 !important;
    background: rgba(99,102,241,0.08) !important;
}

/* ── Expander ────────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid #2d3748 !important;
    border-radius: 8px !important;
    background: #1a1d27 !important;
}
[data-testid="stExpander"] summary {
    color: #94a3b8 !important;
    font-size: 0.85rem !important;
}

/* ── Alert boxes ─────────────────────────────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: 8px !important;
    border-left-width: 3px !important;
}

/* ── Sidebar brand ───────────────────────────────────────────────────────── */
.sidebar-brand {
    padding: 0.75rem 0 1rem;
    border-bottom: 1px solid #2d3748;
    margin-bottom: 1rem;
}
.sidebar-brand h2 {
    font-size: 1.2rem;
    font-weight: 700;
    color: #a5b4fc;
    margin: 0 0 0.2rem 0;
    letter-spacing: -0.02em;
}
.sidebar-brand p {
    font-size: 0.73rem;
    color: #6b7280;
    margin: 0;
}
.session-box {
    background: #111827;
    border: 1px solid #2d3748;
    border-radius: 8px;
    padding: 0.55rem 0.75rem;
    margin-top: 0.75rem;
}
.session-box .s-label {
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #6366f1;
    margin-bottom: 0.2rem;
}
.session-box .s-value {
    font-size: 0.68rem;
    color: #94a3b8;
    font-family: monospace;
    word-break: break-all;
}

/* ── Custom component classes ────────────────────────────────────────────── */

/* Hero title — gradient text */
.hero-title {
    font-size: 1.75rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    background: linear-gradient(135deg, #a5b4fc 0%, #c084fc 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0 0 0.2rem 0;
    line-height: 1.2;
}

/* Answer card */
.answer-card {
    background: linear-gradient(135deg, #1a1d27 0%, #1e2235 100%);
    border: 1px solid #2d3748;
    border-left: 3px solid #6366f1;
    border-radius: 12px;
    padding: 1.4rem 1.5rem;
    margin: 0.75rem 0;
    line-height: 1.75;
    color: #e2e8f0;
    font-size: 0.95rem;
}

/* Source pill badges */
.sources-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    margin-top: 0.75rem;
}
.source-badge {
    display: inline-flex;
    align-items: center;
    background: rgba(99,102,241,0.12);
    border: 1px solid rgba(99,102,241,0.3);
    border-radius: 20px;
    padding: 0.25rem 0.75rem;
    font-size: 0.75rem;
    color: #a5b4fc;
    font-weight: 500;
    white-space: nowrap;
}
.source-badge .score {
    margin-left: 0.4rem;
    opacity: 0.6;
    font-size: 0.68rem;
}

/* Document card (Manage page) */
.doc-card {
    background: #1a1d27;
    border: 1px solid #2d3748;
    border-radius: 10px;
    padding: 0.85rem 1.1rem;
    transition: border-color 0.2s ease;
}
.doc-card:hover { border-color: #4b5563; }
.doc-card .doc-name {
    font-weight: 600;
    color: #e2e8f0;
    font-size: 0.9rem;
    margin-bottom: 0.3rem;
}
.doc-card .doc-meta {
    font-size: 0.73rem;
    color: #6b7280;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
}

/* Visibility badges */
.vis-badge-public {
    display: inline-flex; align-items: center; gap: 0.25rem;
    background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.3);
    border-radius: 12px; padding: 0.1rem 0.55rem;
    font-size: 0.68rem; color: #4ade80; font-weight: 500;
}
.vis-badge-private {
    display: inline-flex; align-items: center; gap: 0.25rem;
    background: rgba(251,191,36,0.1); border: 1px solid rgba(251,191,36,0.3);
    border-radius: 12px; padding: 0.1rem 0.55rem;
    font-size: 0.68rem; color: #fbbf24; font-weight: 500;
}
.vis-badge-other {
    display: inline-flex; align-items: center; gap: 0.25rem;
    background: rgba(148,163,184,0.1); border: 1px solid rgba(148,163,184,0.2);
    border-radius: 12px; padding: 0.1rem 0.55rem;
    font-size: 0.68rem; color: #94a3b8; font-weight: 500;
}

/* Info card (how-it-works panel) */
.info-card {
    background: #1a1d27;
    border: 1px solid #2d3748;
    border-radius: 12px;
    padding: 1.25rem 1.4rem;
    height: 100%;
}
.info-card .info-title {
    font-size: 0.8rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: #6366f1;
    margin-bottom: 0.9rem;
}
.info-card ol {
    padding-left: 1.1rem;
    margin: 0;
    color: #94a3b8;
    font-size: 0.85rem;
    line-height: 2;
}
.info-card .info-footer {
    margin-top: 0.9rem;
    padding-top: 0.75rem;
    border-top: 1px solid #2d3748;
    font-size: 0.73rem;
    color: #4b5563;
}
"""


def inject_css() -> None:
    """Inject all custom CSS into the current Streamlit page."""
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)


def render_sidebar(user_id: str, access_key: str, is_new: bool = False) -> None:
    """Render the branded sidebar with navigation and persistent key UI."""
    from auth import apply_key  # local import to avoid circular at module level

    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
                <h2>⚡ RAG Assistant</h2>
                <p>Retrieval-Augmented Generation</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── Access key section ──────────────────────────────────────────────
        st.markdown(
            "<p style='font-size:0.72rem;font-weight:700;text-transform:uppercase;"
            "letter-spacing:0.07em;color:#6366f1;margin-bottom:0.3rem'>🔑 Access Key</p>",
            unsafe_allow_html=True,
        )

        if is_new:
            st.warning(
                "New key generated — **save it** to keep access to your private documents.",
                icon="⚠️",
            )

        st.code(access_key, language=None)
        st.caption(
            "This key identifies you. Same key = same private documents, "
            "across sessions and devices."
        )

        with st.expander("🔄  Change / restore key"):
            with st.form("change_key_form", clear_on_submit=True):
                new_key = st.text_input(
                    "Your key",
                    placeholder="e.g. A3F7B2C1",
                    label_visibility="collapsed",
                )
                if st.form_submit_button("Apply", use_container_width=True):
                    if new_key.strip():
                        apply_key(new_key.strip())
                        st.rerun()
                    else:
                        st.error("Key cannot be empty.")

        st.divider()

        # ── Navigation ──────────────────────────────────────────────────────
        st.page_link("streamlit_app.py", label="🏠  Upload & Ask")
        st.page_link("pages/1_Manage_Documents.py", label="🗂️  Manage Documents")
        st.divider()
        st.caption("Powered by **Qdrant** · **Inngest** · **Groq**")
