import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.data_source import UserSourcePermission


async def assign_permission(
    db: AsyncSession,
    user_id: uuid.UUID,
    source_id: uuid.UUID,
    permitted_tables: list[str] | None = None,
) -> UserSourcePermission:
    """Assign or replace a user's permission for a source."""
    result = await db.execute(
        select(UserSourcePermission).where(
            UserSourcePermission.user_id == user_id,
            UserSourcePermission.source_id == source_id,
        )
    )
    perm = result.scalar_one_or_none()
    if perm:
        perm.permitted_tables = permitted_tables
    else:
        perm = UserSourcePermission(
            user_id=user_id,
            source_id=source_id,
            permitted_tables=permitted_tables,
        )
        db.add(perm)
    await db.commit()
    await db.refresh(perm)
    return perm


async def get_permitted_tables(
    db: AsyncSession,
    user_id: uuid.UUID,
    source_id: uuid.UUID,
) -> list[str] | None:
    """Return permitted table list, or None if user has full access."""
    result = await db.execute(
        select(UserSourcePermission).where(
            UserSourcePermission.user_id == user_id,
            UserSourcePermission.source_id == source_id,
        )
    )
    perm = result.scalar_one_or_none()
    if not perm:
        return []  # no permission at all
    return perm.permitted_tables  # None = all tables; list = restricted


async def get_user_permissions(db: AsyncSession, user_id: uuid.UUID) -> list[UserSourcePermission]:
    result = await db.execute(
        select(UserSourcePermission).where(UserSourcePermission.user_id == user_id)
    )
    return list(result.scalars().all())


async def revoke_permission(db: AsyncSession, user_id: uuid.UUID, source_id: uuid.UUID) -> None:
    result = await db.execute(
        select(UserSourcePermission).where(
            UserSourcePermission.user_id == user_id,
            UserSourcePermission.source_id == source_id,
        )
    )
    perm = result.scalar_one_or_none()
    if perm:
        await db.delete(perm)
        await db.commit()
