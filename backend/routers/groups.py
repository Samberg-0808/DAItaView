import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_db
from backend.dependencies import require_role
from backend.models.audit import AuditEventType
from backend.models.user import User, UserRole
from backend.services import group_service
from backend.services.audit_service import AuditService

router = APIRouter(prefix="/groups", tags=["groups"])


class CreateGroupRequest(BaseModel):
    name: str
    description: str | None = None


class UpdateGroupRequest(BaseModel):
    name: str | None = None
    description: str | None = None


class AddMemberRequest(BaseModel):
    user_id: uuid.UUID


class AssignPermissionRequest(BaseModel):
    source_id: uuid.UUID
    permitted_tables: list[str] | None = None


@router.get("", dependencies=[Depends(require_role(UserRole.super_admin))])
async def list_groups(db: AsyncSession = Depends(get_db)):
    groups = await group_service.list_groups(db)
    return [
        {
            "id": str(g.id),
            "name": g.name,
            "description": g.description,
            "created_at": g.created_at.isoformat() if g.created_at else None,
            "member_count": len(g.memberships),
            "members": [{"user_id": str(m.user_id)} for m in g.memberships],
        }
        for g in groups
    ]


@router.post("", dependencies=[Depends(require_role(UserRole.super_admin))])
async def create_group(
    body: CreateGroupRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.super_admin)),
):
    try:
        group = await group_service.create_group(db, body.name, body.description)
    except Exception:
        raise HTTPException(status_code=400, detail="Group name already exists")
    await AuditService.log(db, AuditEventType.permission_granted, user_id=current_user.id,
                           details={"action": "group_created", "group_id": str(group.id), "group_name": body.name})
    return {"id": str(group.id), "name": group.name, "description": group.description}


@router.patch("/{group_id}", dependencies=[Depends(require_role(UserRole.super_admin))])
async def update_group(
    group_id: uuid.UUID,
    body: UpdateGroupRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        group = await group_service.update_group(db, group_id, body.name, body.description)
    except ValueError:
        raise HTTPException(status_code=404, detail="Group not found")
    return {"id": str(group.id), "name": group.name, "description": group.description}


@router.delete("/{group_id}", dependencies=[Depends(require_role(UserRole.super_admin))])
async def delete_group(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.super_admin)),
):
    await group_service.delete_group(db, group_id)
    await AuditService.log(db, AuditEventType.permission_revoked, user_id=current_user.id,
                           details={"action": "group_deleted", "group_id": str(group_id)})
    return {"detail": "Group deleted"}


@router.post("/{group_id}/members", dependencies=[Depends(require_role(UserRole.super_admin))])
async def add_member(
    group_id: uuid.UUID,
    body: AddMemberRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.super_admin)),
):
    try:
        await group_service.add_member(db, group_id, body.user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await AuditService.log(db, AuditEventType.permission_granted, user_id=current_user.id,
                           details={"action": "group_member_added", "group_id": str(group_id), "target_user": str(body.user_id)})
    return {"detail": "Member added"}


@router.delete("/{group_id}/members/{user_id}", dependencies=[Depends(require_role(UserRole.super_admin))])
async def remove_member(
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.super_admin)),
):
    await group_service.remove_member(db, group_id, user_id)
    await AuditService.log(db, AuditEventType.permission_revoked, user_id=current_user.id,
                           details={"action": "group_member_removed", "group_id": str(group_id), "target_user": str(user_id)})
    return {"detail": "Member removed"}


@router.get("/{group_id}/permissions", dependencies=[Depends(require_role(UserRole.super_admin))])
async def get_group_permissions(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    perms = await group_service.get_group_permissions(db, group_id)
    return [
        {"source_id": str(p.source_id), "permitted_tables": p.permitted_tables}
        for p in perms
    ]


@router.post("/{group_id}/permissions", dependencies=[Depends(require_role(UserRole.super_admin))])
async def assign_permission(
    group_id: uuid.UUID,
    body: AssignPermissionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.super_admin)),
):
    perm = await group_service.assign_group_permission(db, group_id, body.source_id, body.permitted_tables)
    await AuditService.log(db, AuditEventType.permission_granted, user_id=current_user.id,
                           source_id=body.source_id,
                           details={"action": "group_permission_granted", "group_id": str(group_id), "permitted_tables": body.permitted_tables})
    return {"source_id": str(perm.source_id), "permitted_tables": perm.permitted_tables}


@router.delete("/{group_id}/permissions/{source_id}", dependencies=[Depends(require_role(UserRole.super_admin))])
async def revoke_permission(
    group_id: uuid.UUID,
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.super_admin)),
):
    await group_service.revoke_group_permission(db, group_id, source_id)
    await AuditService.log(db, AuditEventType.permission_revoked, user_id=current_user.id,
                           source_id=source_id,
                           details={"action": "group_permission_revoked", "group_id": str(group_id)})
    return {"detail": "Permission revoked"}
