import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class AuditEventType(str, enum.Enum):
    # Query events
    query_submitted = "query_submitted"
    code_generated = "code_generated"
    code_blocked = "code_blocked"
    query_completed = "query_completed"
    query_failed = "query_failed"
    # Auth events
    login_success = "login_success"
    login_failed = "login_failed"
    logout = "logout"
    sso_login = "sso_login"
    # Admin events
    user_created = "user_created"
    user_role_changed = "user_role_changed"
    source_connected = "source_connected"
    source_deleted = "source_deleted"
    permission_granted = "permission_granted"
    permission_revoked = "permission_revoked"
    knowledge_updated = "knowledge_updated"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[AuditEventType] = mapped_column(Enum(AuditEventType), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=True, index=True)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    user: Mapped["User | None"] = relationship(back_populates="audit_logs")
