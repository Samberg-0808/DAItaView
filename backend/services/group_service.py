import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.group import Group, GroupMembership, GroupSourcePermission


async def create_group(db: AsyncSession, name: str, description: str | None = None) -> Group:
    group = Group(name=name, description=description)
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return group


async def list_groups(db: AsyncSession) -> list[Group]:
    result = await db.execute(
        select(Group)
        .options(selectinload(Group.memberships), selectinload(Group.source_permissions))
        .order_by(Group.created_at)
    )
    return list(result.scalars().all())


async def get_group(db: AsyncSession, group_id: uuid.UUID) -> Group | None:
    result = await db.execute(
        select(Group)
        .options(selectinload(Group.memberships), selectinload(Group.source_permissions))
        .where(Group.id == group_id)
    )
    return result.scalar_one_or_none()


async def update_group(db: AsyncSession, group_id: uuid.UUID, name: str | None = None, description: str | None = None) -> Group:
    group = await get_group(db, group_id)
    if not group:
        raise ValueError(f"Group {group_id} not found")
    if name is not None:
        group.name = name
    if description is not None:
        group.description = description
    await db.commit()
    await db.refresh(group)
    return group


async def delete_group(db: AsyncSession, group_id: uuid.UUID) -> None:
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if group:
        await db.delete(group)
        await db.commit()


async def add_member(db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID) -> GroupMembership:
    existing = await db.execute(
        select(GroupMembership).where(
            GroupMembership.group_id == group_id,
            GroupMembership.user_id == user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("User is already a member of this group")
    membership = GroupMembership(group_id=group_id, user_id=user_id)
    db.add(membership)
    await db.commit()
    await db.refresh(membership)
    return membership


async def remove_member(db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID) -> None:
    result = await db.execute(
        select(GroupMembership).where(
            GroupMembership.group_id == group_id,
            GroupMembership.user_id == user_id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership:
        await db.delete(membership)
        await db.commit()


async def assign_group_permission(
    db: AsyncSession,
    group_id: uuid.UUID,
    source_id: uuid.UUID,
    permitted_tables: list[str] | None = None,
) -> GroupSourcePermission:
    result = await db.execute(
        select(GroupSourcePermission).where(
            GroupSourcePermission.group_id == group_id,
            GroupSourcePermission.source_id == source_id,
        )
    )
    perm = result.scalar_one_or_none()
    if perm:
        perm.permitted_tables = permitted_tables
    else:
        perm = GroupSourcePermission(
            group_id=group_id,
            source_id=source_id,
            permitted_tables=permitted_tables,
        )
        db.add(perm)
    await db.commit()
    await db.refresh(perm)
    return perm


async def revoke_group_permission(db: AsyncSession, group_id: uuid.UUID, source_id: uuid.UUID) -> None:
    result = await db.execute(
        select(GroupSourcePermission).where(
            GroupSourcePermission.group_id == group_id,
            GroupSourcePermission.source_id == source_id,
        )
    )
    perm = result.scalar_one_or_none()
    if perm:
        await db.delete(perm)
        await db.commit()


async def get_group_permissions(db: AsyncSession, group_id: uuid.UUID) -> list[GroupSourcePermission]:
    result = await db.execute(
        select(GroupSourcePermission).where(GroupSourcePermission.group_id == group_id)
    )
    return list(result.scalars().all())


async def get_user_groups(db: AsyncSession, user_id: uuid.UUID) -> list[uuid.UUID]:
    result = await db.execute(
        select(GroupMembership.group_id).where(GroupMembership.user_id == user_id)
    )
    return list(result.scalars().all())
