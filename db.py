"""SQLite persistence for ingested document metadata and LLM config."""

import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.getenv("DB_PATH", str(Path(__file__).parent / "ragapp.db")))


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


_llm_config_lock = threading.Lock()


def init_db() -> None:
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                source_id   TEXT PRIMARY KEY,
                user_id     TEXT NOT NULL DEFAULT 'anonymous',
                visibility  TEXT NOT NULL DEFAULT 'private',
                ingested_at TEXT NOT NULL,
                chunk_count INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS llm_config (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)


def upsert_document(source_id: str, user_id: str, visibility: str, chunk_count: int) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO documents (source_id, user_id, visibility, ingested_at, chunk_count)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(source_id) DO UPDATE SET
                user_id     = excluded.user_id,
                visibility  = excluded.visibility,
                ingested_at = excluded.ingested_at,
                chunk_count = excluded.chunk_count
            """,
            (source_id, user_id, visibility, datetime.now(timezone.utc).isoformat(), chunk_count),
        )


def list_documents(user_id: str | None = None) -> list[sqlite3.Row]:
    with _connect() as conn:
        if user_id:
            return conn.execute(
                """
                SELECT * FROM documents
                WHERE user_id = ? OR visibility = 'public'
                ORDER BY ingested_at DESC
                """,
                (user_id,),
            ).fetchall()
        return conn.execute(
            "SELECT * FROM documents ORDER BY ingested_at DESC"
        ).fetchall()


def update_visibility(source_id: str, visibility: str, user_id: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE documents SET visibility = ? WHERE source_id = ? AND user_id = ?",
            (visibility, source_id, user_id),
        )


def delete_document(source_id: str, user_id: str) -> None:
    with _connect() as conn:
        conn.execute(
            "DELETE FROM documents WHERE source_id = ? AND user_id = ?",
            (source_id, user_id),
        )


def get_llm_config() -> dict[str, str]:
    """Return stored LLM config keys, or empty dict if none saved yet."""
    with _llm_config_lock, _connect() as conn:
        rows = conn.execute("SELECT key, value FROM llm_config").fetchall()
    return {r["key"]: r["value"] for r in rows}


def set_llm_config(config: dict[str, str]) -> None:
    """Persist all key/value pairs atomically, replacing existing values."""
    with _llm_config_lock, _connect() as conn:
        conn.executemany(
            "INSERT INTO llm_config (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            config.items(),
        )
