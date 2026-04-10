"""Audit service — never raises; audit failure must never block a user action."""
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.audit import AuditEventType, AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    @staticmethod
    async def log(
        db: AsyncSession,
        event_type: AuditEventType,
        user_id: uuid.UUID | None = None,
        source_id: uuid.UUID | None = None,
        details: dict | None = None,
    ) -> None:
        try:
            record = AuditLog(
                event_type=event_type,
                user_id=user_id,
                source_id=source_id,
                details=details or {},
            )
            db.add(record)
            await db.commit()
        except Exception:
            logger.exception("Failed to write audit log — swallowing error")
