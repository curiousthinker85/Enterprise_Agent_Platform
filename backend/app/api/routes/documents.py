from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.workspace import Workspace
from app.models.user import User
from app.models.workspace_member import WorkspaceRole
from app.schemas.documents import DocumentChunksResponse, DocumentIndexResponse, DocumentProcessResponse, DocumentResponse
from app.services.document_processor import DocumentProcessingError, process_document
from app.services.storage import save_upload
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.vector_store import VectorStore, get_vector_store
from app.services.auth_service import get_current_user
from app.services.audit_service import log_action
from app.services.workspace_access import require_workspace_role

router = APIRouter(tags=["documents"])


@router.post("/workspaces/{workspace_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(workspace_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Document:
    require_workspace_role(db, current_user, workspace_id, {WorkspaceRole.ADMIN, WorkspaceRole.MEMBER})
    if not file.filename:
        raise HTTPException(status_code=422, detail="A filename is required")

    original_filename = file.filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    document = Document(
        workspace_id=workspace_id,
        original_filename=original_filename,
        stored_filename=original_filename,
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=0,
    )
    db.add(document)
    db.flush()
    try:
        stored_filename, size_bytes = save_upload(workspace_id, document.id, file)
        document.stored_filename = stored_filename
        document.size_bytes = size_bytes
        log_action(db, "document.upload", current_user.id, workspace_id, "document", str(document.id), {"filename": original_filename})
        db.commit()
        db.refresh(document)
        return document
    except OSError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to store uploaded file") from exc
    finally:
        file.file.close()


@router.get("/workspaces/{workspace_id}/documents", response_model=list[DocumentResponse])
def list_documents(workspace_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[Document]:
    require_workspace_role(db, current_user, workspace_id, {WorkspaceRole.ADMIN, WorkspaceRole.MEMBER, WorkspaceRole.VIEWER})
    return list(db.scalars(select(Document).where(Document.workspace_id == workspace_id).order_by(Document.created_at.desc())))


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(document_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    require_workspace_role(db, current_user, document.workspace_id, {WorkspaceRole.ADMIN, WorkspaceRole.MEMBER, WorkspaceRole.VIEWER})
    return document


@router.post("/documents/{document_id}/process", response_model=DocumentProcessResponse)
def process_uploaded_document(document_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> DocumentProcessResponse:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    require_workspace_role(db, current_user, document.workspace_id, {WorkspaceRole.ADMIN, WorkspaceRole.MEMBER})
    try:
        chunk_count = process_document(db, document)
    except DocumentProcessingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.refresh(document)
    document_data = DocumentResponse.model_validate(document, from_attributes=True).model_dump()
    log_action(db, "document.process", current_user.id, document.workspace_id, "document", str(document.id), {"chunk_count": chunk_count})
    db.commit()
    return DocumentProcessResponse(**document_data, chunk_count=chunk_count)


@router.get("/documents/{document_id}/chunks", response_model=DocumentChunksResponse)
def get_document_chunks(document_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> DocumentChunksResponse:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    require_workspace_role(db, current_user, document.workspace_id, {WorkspaceRole.ADMIN, WorkspaceRole.MEMBER, WorkspaceRole.VIEWER})
    chunks = list(db.scalars(select(DocumentChunk).where(DocumentChunk.document_id == document_id).order_by(DocumentChunk.chunk_index)))
    return DocumentChunksResponse(document_id=document.id, status=document.status, total_chunks=len(chunks), chunks=chunks)


@router.post("/documents/{document_id}/index", response_model=DocumentIndexResponse)
def index_document(
    document_id: int,
    db: Session = Depends(get_db),
    embeddings: EmbeddingService = Depends(get_embedding_service),
    vector_store: VectorStore = Depends(get_vector_store),
    current_user: User = Depends(get_current_user),
) -> DocumentIndexResponse:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    require_workspace_role(db, current_user, document.workspace_id, {WorkspaceRole.ADMIN, WorkspaceRole.MEMBER})
    if document.status != "processed":
        raise HTTPException(status_code=409, detail="Document must be processed before indexing")
    chunks = list(db.scalars(select(DocumentChunk).where(DocumentChunk.document_id == document_id).order_by(DocumentChunk.chunk_index)))
    try:
        vector_store.upsert_chunks(chunks, document.original_filename, embeddings.embed_texts([chunk.content for chunk in chunks]))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Document indexing failed: {exc}") from exc
    document.status = "indexed"
    log_action(db, "document.index", current_user.id, document.workspace_id, "document", str(document.id), {"chunks_indexed": len(chunks)})
    db.commit()
    return DocumentIndexResponse(document_id=document.id, status=document.status, chunks_indexed=len(chunks))
