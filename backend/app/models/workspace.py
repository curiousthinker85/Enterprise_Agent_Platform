from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class WorkspaceType(str, Enum):
    HR = "HR"
    FINANCE = "FINANCE"
    AUDIT = "AUDIT"
    GENERAL = "GENERAL"


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    workspace_type: Mapped[WorkspaceType] = mapped_column(SqlEnum(WorkspaceType), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    documents: Mapped[list["Document"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
