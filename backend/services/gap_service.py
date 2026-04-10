import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.knowledge import KnowledgeGapSignal


async def record_gap_signal(
    db: AsyncSession,
    source_id: uuid.UUID,
    question_text: str,
) -> None:
    """Upsert a knowledge gap signal — increment frequency if similar text exists."""
    # Simple exact-match dedup for now; fuzzy matching can be added later
    result = await db.execute(
        select(KnowledgeGapSignal).where(
            KnowledgeGapSignal.source_id == source_id,
            KnowledgeGapSignal.question_text == question_text,
            KnowledgeGapSignal.resolved == False,
        )
    )
    signal = result.scalar_one_or_none()
    if signal:
        signal.frequency += 1
        signal.last_seen_at = datetime.now(timezone.utc)
    else:
        signal = KnowledgeGapSignal(
            source_id=source_id,
            question_text=question_text,
            frequency=1,
        )
        db.add(signal)
    await db.commit()


async def list_gaps(
    db: AsyncSession,
    source_id: uuid.UUID,
    resolved: bool = False,
) -> list[KnowledgeGapSignal]:
    result = await db.execute(
        select(KnowledgeGapSignal)
        .where(KnowledgeGapSignal.source_id == source_id, KnowledgeGapSignal.resolved == resolved)
        .order_by(KnowledgeGapSignal.frequency.desc())
    )
    return list(result.scalars().all())


async def resolve_gap(db: AsyncSession, gap_id: uuid.UUID) -> None:
    result = await db.execute(select(KnowledgeGapSignal).where(KnowledgeGapSignal.id == gap_id))
    signal = result.scalar_one_or_none()
    if signal:
        signal.resolved = True
        await db.commit()
