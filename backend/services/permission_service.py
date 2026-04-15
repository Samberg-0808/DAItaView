import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.group import GroupMembership, GroupSourcePermission


async def get_permitted_tables(
    db: AsyncSession,
    user_id: uuid.UUID,
    source_id: uuid.UUID,
) -> list[str] | None:
    """Return permitted table list based on group memberships (union semantics).

    Returns:
        None  — full access (at least one group grants all tables)
        []    — no access at all
        [..]  — restricted to these specific tables
    """
    group_ids_result = await db.execute(
        select(GroupMembership.group_id).where(GroupMembership.user_id == user_id)
    )
    group_ids = list(group_ids_result.scalars().all())

    if not group_ids:
        return []

    gp_result = await db.execute(
        select(GroupSourcePermission).where(
            GroupSourcePermission.group_id.in_(group_ids),
            GroupSourcePermission.source_id == source_id,
        )
    )
    group_perms = list(gp_result.scalars().all())

    if not group_perms:
        return []

    for gp in group_perms:
        if gp.permitted_tables is None:
            return None  # full access via group

    all_tables: set[str] = set()
    for gp in group_perms:
        if gp.permitted_tables:
            all_tables.update(gp.permitted_tables)

    return sorted(all_tables) if all_tables else []
