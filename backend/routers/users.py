import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_db
from backend.dependencies import require_role
from backend.models.user import User, UserRole
from backend.services.audit_service import AuditService
from backend.models.audit import AuditEventType
from backend.services import permission_service, user_service

router = APIRouter(prefix="/users", tags=["users"])


class CreateUserRequest(BaseModel):
    email: str
    username: str
    password: str
    role: UserRole = UserRole.user


class UpdateRoleRequest(BaseModel):
    role: UserRole


class AssignPermissionRequest(BaseModel):
    source_id: uuid.UUID
    permitted_tables: list[str] | None = None  # None = full access


@router.get("", dependencies=[Depends(require_role(UserRole.super_admin))])
async def list_users(db: AsyncSession = Depends(get_db)):
    users = await user_service.list_users(db)
    return users


@router.post("", dependencies=[Depends(require_role(UserRole.super_admin))])
async def create_user(
    body: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.super_admin)),
):
    user = await user_service.create_user(db, body.email, body.username, body.password, body.role)
    await AuditService.log(db, AuditEventType.user_created, user_id=current_user.id, details={"created_user": str(user.id)})
    return user


@router.patch("/{user_id}", dependencies=[Depends(require_role(UserRole.super_admin))])
async def update_role(
    user_id: uuid.UUID,
    body: UpdateRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.super_admin)),
):
    user = await user_service.update_role(db, user_id, body.role)
    await AuditService.log(db, AuditEventType.user_role_changed, user_id=current_user.id, details={"target_user": str(user_id), "new_role": body.role.value})
    return user


@router.delete("/{user_id}", dependencies=[Depends(require_role(UserRole.super_admin))])
async def deactivate_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await user_service.deactivate_user(db, user_id)
    return {"detail": "User deactivated"}


@router.get("/{user_id}/permissions")
async def get_permissions(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.super_admin, UserRole.data_admin)),
):
    return await permission_service.get_user_permissions(db, user_id)


@router.post("/{user_id}/permissions")
async def assign_permission(
    user_id: uuid.UUID,
    body: AssignPermissionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.super_admin, UserRole.data_admin)),
):
    perm = await permission_service.assign_permission(db, user_id, body.source_id, body.permitted_tables)
    await AuditService.log(db, AuditEventType.permission_granted, user_id=current_user.id,
                           source_id=body.source_id,
                           details={"target_user": str(user_id), "permitted_tables": body.permitted_tables})
    return perm


@router.delete("/{user_id}/permissions/{source_id}")
async def revoke_permission(
    user_id: uuid.UUID,
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.super_admin, UserRole.data_admin)),
):
    await permission_service.revoke_permission(db, user_id, source_id)
    await AuditService.log(db, AuditEventType.permission_revoked, user_id=current_user.id,
                           source_id=source_id, details={"target_user": str(user_id)})
    return {"detail": "Permission revoked"}
