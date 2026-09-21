from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.workspace import WorkspaceType


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    workspace_type: WorkspaceType


class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    workspace_type: WorkspaceType
    created_at: datetime


class SearchResult(BaseModel):
    document_id: int
    document_filename: str
    chunk_index: int
    content: str
    score: float


class WorkspaceSearchResponse(BaseModel):
    workspace_id: int
    query: str
    results: list[SearchResult]
