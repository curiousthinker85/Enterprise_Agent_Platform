from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.models.workspace_member import WorkspaceMember, WorkspaceRole
from app.schemas.audit import AuditLogResponse
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/audit-logs", tags=["audit logs"])


@router.get("", response_model=list[AuditLogResponse])
def list_audit_logs(
    workspace_id: int | None = None,
    action: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AuditLog]:
    statement = select(AuditLog)
    if not current_user.is_superuser:
        admin_workspace_ids = select(WorkspaceMember.workspace_id).where(WorkspaceMember.user_id == current_user.id, WorkspaceMember.role == WorkspaceRole.ADMIN)
        if workspace_id is not None:
            if workspace_id not in set(db.scalars(admin_workspace_ids)):
                raise HTTPException(status_code=403, detail="Administrator access to the workspace is required")
            statement = statement.where(AuditLog.workspace_id == workspace_id)
        else:
            statement = statement.where(AuditLog.workspace_id.in_(admin_workspace_ids))
    elif workspace_id is not None:
        statement = statement.where(AuditLog.workspace_id == workspace_id)
    if action:
        statement = statement.where(AuditLog.action == action)
    return list(db.scalars(statement.order_by(AuditLog.created_at.desc()).limit(limit)))
