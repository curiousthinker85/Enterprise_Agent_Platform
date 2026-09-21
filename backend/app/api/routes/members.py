from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.workspace_member import WorkspaceMember, WorkspaceRole
from app.schemas.members import WorkspaceMemberCreate, WorkspaceMemberResponse
from app.services.audit_service import log_action
from app.services.auth_service import get_current_user
from app.services.workspace_access import require_workspace_role

router = APIRouter(prefix="/workspaces/{workspace_id}/members", tags=["workspace members"])


@router.post("", response_model=WorkspaceMemberResponse, status_code=status.HTTP_201_CREATED)
def add_member(
    workspace_id: int,
    payload: WorkspaceMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkspaceMemberResponse:
    require_workspace_role(db, current_user, workspace_id, {WorkspaceRole.ADMIN})
    user = db.scalar(select(User).where(User.email == str(payload.email).lower()))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    member = db.scalar(select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user.id))
    if member is None:
        member = WorkspaceMember(workspace_id=workspace_id, user_id=user.id, role=payload.role)
        db.add(member)
    else:
        member.role = payload.role
    db.flush()
    log_action(db, "workspace.member.add", current_user.id, workspace_id, "user", str(user.id), {"role": payload.role.value})
    db.commit()
    db.refresh(member)
    return WorkspaceMemberResponse(id=member.id, user_id=user.id, email=user.email, full_name=user.full_name, role=member.role, created_at=member.created_at)


@router.get("", response_model=list[WorkspaceMemberResponse])
def list_members(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[WorkspaceMemberResponse]:
    require_workspace_role(db, current_user, workspace_id, {WorkspaceRole.ADMIN, WorkspaceRole.MEMBER, WorkspaceRole.VIEWER})
    rows = db.execute(
        select(WorkspaceMember, User).join(User, WorkspaceMember.user_id == User.id).where(WorkspaceMember.workspace_id == workspace_id)
    ).all()
    return [WorkspaceMemberResponse(id=member.id, user_id=user.id, email=user.email, full_name=user.full_name, role=member.role, created_at=member.created_at) for member, user in rows]
