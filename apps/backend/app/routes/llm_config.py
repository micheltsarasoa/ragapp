from fastapi import APIRouter

from app.core.llm import get_llm_config, set_llm_config
from app.models.llm import LLMConfig

router = APIRouter()


@router.get("/api/llm_config")
def get_llm_config_endpoint():
    """Return the active LLM config (API key masked)."""
    cfg = get_llm_config()
    return {
        "base_url": cfg["base_url"],
        "model": cfg["model"],
        "api_key_set": bool(cfg["api_key"]),
    }


@router.post("/api/llm_config")
def set_llm_config_endpoint(cfg: LLMConfig):
    """Hot-swap the LLM provider without restarting the server."""
    set_llm_config(cfg.model_dump())
    return {"status": "ok", "model": cfg.model, "base_url": cfg.base_url}
