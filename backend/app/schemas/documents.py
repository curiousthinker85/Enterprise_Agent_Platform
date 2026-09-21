from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    original_filename: str
    stored_filename: str
    mime_type: str
    size_bytes: int
    status: str
    created_at: datetime


class DocumentProcessResponse(DocumentResponse):
    chunk_count: int


class DocumentChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chunk_index: int
    content: str
    char_count: int


class DocumentChunksResponse(BaseModel):
    document_id: int
    status: str
    total_chunks: int
    chunks: list[DocumentChunkResponse]


class DocumentIndexResponse(BaseModel):
    document_id: int
    status: str
    chunks_indexed: int
