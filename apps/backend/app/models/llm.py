from pydantic import BaseModel


class LLMConfig(BaseModel):
    base_url: str
    api_key: str
    model: str
