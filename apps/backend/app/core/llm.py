import threading

from openai import AsyncOpenAI, OpenAI

from app.core import db
from app.core.config import ENV_LLM_DEFAULTS, MAX_CONTEXT_CHARS

_llm_lock = threading.Lock()


def get_llm_config() -> dict[str, str]:
    with _llm_lock:
        stored = db.get_llm_config()
    return {**ENV_LLM_DEFAULTS, **stored}


def set_llm_config(config: dict[str, str]) -> None:
    with _llm_lock:
        db.set_llm_config(config)


def sync_client() -> OpenAI:
    cfg = get_llm_config()
    return OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])


def async_client() -> AsyncOpenAI:
    cfg = get_llm_config()
    return AsyncOpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])


def truncate_contexts(contexts: list[str]) -> list[str]:
    result, used = [], 0
    for ctx in contexts:
        if used + len(ctx) > MAX_CONTEXT_CHARS:
            break
        result.append(ctx)
        used += len(ctx)
    return result


def build_rag_messages(question: str, contexts: list[str]) -> list[dict]:
    context_block = "\n\n".join(f"- {c}" for c in contexts)
    return [
        {"role": "system", "content": "You answer questions using only the provided context."},
        {
            "role": "user",
            "content": (
                "Use the following context to answer the question.\n\n"
                f"Context:\n{context_block}\n\n"
                f"Question: {question}\n"
                "Answer concisely using the context above."
            ),
        },
    ]
