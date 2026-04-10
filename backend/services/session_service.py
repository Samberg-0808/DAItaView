import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.session import ChatSession, SessionTurn


async def create_session(
    db: AsyncSession,
    user_id: uuid.UUID,
    source_id: uuid.UUID,
) -> ChatSession:
    session = ChatSession(user_id=user_id, source_id=source_id, title="New Chat")
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session(db: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID) -> ChatSession | None:
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.id == session_id, ChatSession.user_id == user_id)
        .options(selectinload(ChatSession.turns))
    )
    return result.scalar_one_or_none()


async def list_sessions(db: AsyncSession, user_id: uuid.UUID) -> list[ChatSession]:
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user_id)
        .order_by(ChatSession.is_pinned.desc(), ChatSession.last_active_at.desc())
    )
    return list(result.scalars().all())


async def rename_session(db: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID, title: str) -> ChatSession:
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id))
    session = result.scalar_one_or_none()
    if not session:
        raise ValueError("Session not found")
    session.title = title[:255]
    await db.commit()
    await db.refresh(session)
    return session


async def pin_session(db: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID, pinned: bool) -> ChatSession:
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id))
    session = result.scalar_one_or_none()
    if not session:
        raise ValueError("Session not found")
    session.is_pinned = pinned
    await db.commit()
    await db.refresh(session)
    return session


async def delete_session(db: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID) -> None:
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id))
    session = result.scalar_one_or_none()
    if session:
        await db.delete(session)
        await db.commit()


async def touch_session(db: AsyncSession, session_id: uuid.UUID) -> None:
    await db.execute(
        update(ChatSession)
        .where(ChatSession.id == session_id)
        .values(last_active_at=datetime.now(timezone.utc))
    )
    await db.commit()
