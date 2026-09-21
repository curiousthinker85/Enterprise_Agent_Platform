from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.workspace_member import WorkspaceRole


class WorkspaceMemberCreate(BaseModel):
    email: EmailStr
    role: WorkspaceRole


class WorkspaceMemberResponse(BaseModel):
    id: int
    user_id: int
    email: EmailStr
    full_name: str
    role: WorkspaceRole
    created_at: datetime
