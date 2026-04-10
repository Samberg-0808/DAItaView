import csv
import io
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_db
from backend.dependencies import require_role
from backend.models.audit import AuditEventType, AuditLog
from backend.models.user import User, UserRole

router = APIRouter(prefix="/audit", tags=["audit"])

_super_admin = Depends(require_role(UserRole.super_admin))


@router.get("", dependencies=[_super_admin])
async def list_audit(
    user_id: uuid.UUID | None = Query(None),
    event_type: AuditEventType | None = Query(None),
    source_id: uuid.UUID | None = Query(None),
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
    limit: int = Query(200, le=1000),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    q = select(AuditLog).order_by(AuditLog.created_at.desc())
    if user_id:
        q = q.where(AuditLog.user_id == user_id)
    if event_type:
        q = q.where(AuditLog.event_type == event_type)
    if source_id:
        q = q.where(AuditLog.source_id == source_id)
    if from_date:
        q = q.where(AuditLog.created_at >= from_date)
    if to_date:
        q = q.where(AuditLog.created_at <= to_date)
    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    return list(result.scalars().all())


@router.get("/export", dependencies=[_super_admin])
async def export_audit(
    user_id: uuid.UUID | None = Query(None),
    event_type: AuditEventType | None = Query(None),
    source_id: uuid.UUID | None = Query(None),
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(AuditLog).order_by(AuditLog.created_at.desc())
    if user_id:
        q = q.where(AuditLog.user_id == user_id)
    if event_type:
        q = q.where(AuditLog.event_type == event_type)
    if source_id:
        q = q.where(AuditLog.source_id == source_id)
    if from_date:
        q = q.where(AuditLog.created_at >= from_date)
    if to_date:
        q = q.where(AuditLog.created_at <= to_date)

    result = await db.execute(q)
    rows = list(result.scalars().all())

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "event_type", "user_id", "source_id", "details", "created_at"])
    for r in rows:
        writer.writerow([r.id, r.event_type.value, r.user_id, r.source_id, r.details, r.created_at])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_log.csv"},
    )
