import pydantic


class RAGChunkAndSrc(pydantic.BaseModel):
    chunks: list[str]
    source_id: str | None = None
    user_id: str = "anonymous"
    visibility: str = "private"


class RAGUpsertResult(pydantic.BaseModel):
    ingested: int


class RAGSearchResult(pydantic.BaseModel):
    contexts: list[str]
    sources: list[str]
    scores: list[float] = []


class RAGQueryResult(pydantic.BaseModel):
    answer: str
    sources: list[str]
    scores: list[float] = []
    num_contexts: int
