import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_db
from backend.dependencies import require_role
from backend.models.audit import AuditEventType
from backend.models.user import User, UserRole
from backend.services.audit_service import AuditService
from backend.services import gap_service
from backend.services.knowledge_service import KnowledgeLayer, KnowledgeService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

_admin = Depends(require_role(UserRole.super_admin, UserRole.data_admin))


class WriteFileRequest(BaseModel):
    layer: KnowledgeLayer
    name: str = ""
    content: str


@router.get("/{source_id}")
async def list_files(source_id: uuid.UUID, _: User = _admin):
    return KnowledgeService.list_files(source_id)


@router.get("/{source_id}/file")
async def read_file(
    source_id: uuid.UUID,
    layer: KnowledgeLayer,
    name: str = "",
    _: User = _admin,
):
    content = KnowledgeService.read_file(source_id, layer, name)
    if content is None:
        raise HTTPException(status_code=404, detail="Knowledge file not found")
    return {"content": content}


@router.put("/{source_id}/file")
async def write_file(
    source_id: uuid.UUID,
    body: WriteFileRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.super_admin, UserRole.data_admin)),
):
    KnowledgeService.write_file(source_id, body.layer, body.name, body.content)
    await AuditService.log(
        db, AuditEventType.knowledge_updated,
        user_id=current_user.id, source_id=source_id,
        details={"layer": body.layer, "name": body.name},
    )
    return {"detail": "Saved"}


@router.delete("/{source_id}/file")
async def delete_file(
    source_id: uuid.UUID,
    layer: KnowledgeLayer,
    name: str = "",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.super_admin, UserRole.data_admin)),
):
    KnowledgeService.delete_file(source_id, layer, name)
    await AuditService.log(
        db, AuditEventType.knowledge_updated,
        user_id=current_user.id, source_id=source_id,
        details={"action": "delete", "layer": layer, "name": name},
    )
    return {"detail": "Deleted"}


@router.get("/{source_id}/gaps")
async def list_gaps(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    return await gap_service.list_gaps(db, source_id, resolved=False)


@router.post("/{source_id}/gaps/{gap_id}/resolve")
async def resolve_gap(
    source_id: uuid.UUID,
    gap_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    await gap_service.resolve_gap(db, gap_id)
    return {"detail": "Gap resolved"}
