from app.schemas.chat import Usage
from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    document_ids: list[int] = Field(default_factory=list)


class Citation(BaseModel):
    citation_index: int
    document_id: int
    document_filename: str
    chunk_index: int
    content: str
    score: float


class AskResponse(BaseModel):
    workspace_id: int
    question: str
    answer: str
    model: str | None = None
    citations: list[Citation]
    usage: Usage | None = None
