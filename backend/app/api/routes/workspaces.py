from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember, WorkspaceRole
from app.schemas.workspaces import WorkspaceCreate, WorkspaceResponse, WorkspaceSearchResponse
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.schemas.rag import AskRequest, AskResponse
from app.services.llm_gateway import LLMGateway, get_gateway
from app.services.rag_service import RAGService
from app.services.auth_service import get_current_user
from app.services.audit_service import log_action
from app.services.workspace_access import require_workspace_role
from app.services.vector_store import VectorStore, get_vector_store

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(payload: WorkspaceCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Workspace:
    workspace = Workspace(**payload.model_dump())
    db.add(workspace)
    db.flush()
    db.add(WorkspaceMember(workspace_id=workspace.id, user_id=current_user.id, role=WorkspaceRole.ADMIN))
    log_action(db, "workspace.create", current_user.id, workspace.id, "workspace", str(workspace.id), {"name": workspace.name})
    db.commit()
    db.refresh(workspace)
    return workspace


@router.get("", response_model=list[WorkspaceResponse])
def list_workspaces(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[Workspace]:
    if current_user.is_superuser:
        return list(db.scalars(select(Workspace).order_by(Workspace.created_at.desc())))
    member_workspace_ids = select(WorkspaceMember.workspace_id).where(WorkspaceMember.user_id == current_user.id)
    return list(db.scalars(select(Workspace).where(Workspace.id.in_(member_workspace_ids)).order_by(Workspace.created_at.desc())))


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(workspace_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Workspace:
    return require_workspace_role(db, current_user, workspace_id, {WorkspaceRole.ADMIN, WorkspaceRole.MEMBER, WorkspaceRole.VIEWER})


@router.get("/{workspace_id}/search", response_model=WorkspaceSearchResponse)
def search_workspace(
    workspace_id: int,
    q: str = Query(min_length=1),
    top_k: int = Query(default=5, ge=1, le=50),
    document_id: int | None = None,
    db: Session = Depends(get_db),
    embeddings: EmbeddingService = Depends(get_embedding_service),
    vector_store: VectorStore = Depends(get_vector_store),
    current_user: User = Depends(get_current_user),
) -> WorkspaceSearchResponse:
    require_workspace_role(db, current_user, workspace_id, {WorkspaceRole.ADMIN, WorkspaceRole.MEMBER, WorkspaceRole.VIEWER})
    query_embedding = embeddings.embed_texts([q])[0]
    results = vector_store.search(query_embedding, workspace_id=workspace_id, top_k=top_k, document_id=document_id)
    return WorkspaceSearchResponse(workspace_id=workspace_id, query=q, results=results)


@router.post("/{workspace_id}/ask", response_model=AskResponse)
async def ask_workspace(
    workspace_id: int,
    request: AskRequest,
    db: Session = Depends(get_db),
    embeddings: EmbeddingService = Depends(get_embedding_service),
    vector_store: VectorStore = Depends(get_vector_store),
    gateway: LLMGateway = Depends(get_gateway),
    current_user: User = Depends(get_current_user),
) -> AskResponse:
    require_workspace_role(db, current_user, workspace_id, {WorkspaceRole.ADMIN, WorkspaceRole.MEMBER, WorkspaceRole.VIEWER})
    response = await RAGService(embeddings, vector_store, gateway).ask(
        workspace_id=workspace_id,
        question=request.question,
        top_k=request.top_k,
        document_ids=request.document_ids,
    )
    log_action(db, "rag.ask", current_user.id, workspace_id, "workspace", str(workspace_id), {"top_k": request.top_k})
    db.commit()
    return response
