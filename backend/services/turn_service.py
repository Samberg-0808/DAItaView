import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.session import SessionTurn, TurnResultType


async def create_turn(
    db: AsyncSession,
    session_id: uuid.UUID,
    question: str,
) -> SessionTurn:
    result = await db.execute(
        select(func.max(SessionTurn.sequence)).where(SessionTurn.session_id == session_id)
    )
    max_seq = result.scalar() or 0
    turn = SessionTurn(session_id=session_id, sequence=max_seq + 1, question=question)
    db.add(turn)
    await db.commit()
    await db.refresh(turn)
    return turn


async def update_turn(
    db: AsyncSession,
    turn_id: uuid.UUID,
    thinking: str | None = None,
    clarification_qa: list | None = None,
    generated_code: str | None = None,
    result_cache: dict | None = None,
    result_type: TurnResultType | None = None,
) -> SessionTurn:
    result = await db.execute(select(SessionTurn).where(SessionTurn.id == turn_id))
    turn = result.scalar_one_or_none()
    if not turn:
        raise ValueError(f"Turn {turn_id} not found")
    if thinking is not None:
        turn.thinking = thinking
    if clarification_qa is not None:
        turn.clarification_qa = clarification_qa
    if generated_code is not None:
        turn.generated_code = generated_code
    if result_cache is not None:
        turn.result_cache = result_cache
        turn.data_snapshot_at = datetime.now(timezone.utc)
        turn.executed_at = datetime.now(timezone.utc)
    if result_type is not None:
        turn.result_type = result_type
    await db.commit()
    await db.refresh(turn)
    return turn


async def get_turns(db: AsyncSession, session_id: uuid.UUID) -> list[SessionTurn]:
    result = await db.execute(
        select(SessionTurn)
        .where(SessionTurn.session_id == session_id)
        .order_by(SessionTurn.sequence)
    )
    return list(result.scalars().all())


async def get_turn(db: AsyncSession, turn_id: uuid.UUID) -> SessionTurn | None:
    result = await db.execute(select(SessionTurn).where(SessionTurn.id == turn_id))
    return result.scalar_one_or_none()
