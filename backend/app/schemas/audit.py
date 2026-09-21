from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    workspace_id: int | None
    action: str
    resource_type: str | None
    resource_id: str | None
    detail: dict[str, Any] | None
    created_at: datetime
