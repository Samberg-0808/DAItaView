"""
QueryPipeline — orchestrates the full turn lifecycle:
  thinking → clarify? → generate code → safety scan → permission check → execute → save → audit
"""
from __future__ import annotations

import uuid
from typing import AsyncGenerator

import httpx

from backend.config import settings
from backend.models.audit import AuditEventType
from backend.models.session import TurnResultType
from backend.services import gap_service, turn_service, session_service
from backend.services.audit_service import AuditService
from backend.services.code_generation import (
    ClarificationRequest,
    GeneratedCode,
    generate_code,
    scan_dangerous_patterns,
    validate_table_permissions,
)
from backend.services.data_source_manager import DataSourceManager, decrypt_config
from backend.services.permission_service import get_permitted_tables


async def stream_turn(
    db,
    session_id: uuid.UUID,
    user_id: uuid.UUID,
    question: str,
    clarification_answers: list[dict] | None = None,
) -> AsyncGenerator[dict, None]:
    """
    Yield status events: {"event": ..., "data": ...}
    Events: thinking | clarifying | generating | executing | done | error
    """
    from backend.services.data_source_manager import DataSourceManager

    # --- Setup ---
    session = await session_service.get_session(db, session_id, user_id)
    if not session:
        yield {"event": "error", "data": {"message": "Session not found"}}
        return

    permitted_tables = await get_permitted_tables(db, user_id, session.source_id)
    if permitted_tables == []:
        yield {"event": "error", "data": {"message": "No access to this data source"}}
        return

    dsm = DataSourceManager(db)
    try:
        full_schema = await dsm.extract_schema(session.source_id)
    except Exception as e:
        yield {"event": "error", "data": {"message": f"Schema extraction failed: {e}"}}
        return
    schema = dsm.get_filtered_schema(full_schema, permitted_tables)

    # Build question history from prior turns (questions + clarification Q&A only)
    prior_turns = await turn_service.get_turns(db, session_id)
    history_turns = [
        {"question": t.question, "clarification_qa": t.clarification_qa}
        for t in prior_turns
    ]

    # Create turn record
    turn = await turn_service.create_turn(db, session_id, question)

    # If resuming after clarification, attach Q&A to this turn
    if clarification_answers:
        await turn_service.update_turn(db, turn.id, clarification_qa=clarification_answers)
        history_turns.append({"question": question, "clarification_qa": clarification_answers})

    await AuditService.log(db, AuditEventType.query_submitted, user_id=user_id,
                           source_id=session.source_id, details={"session_id": str(session_id)})

    # --- Generation with retry ---
    yield {"event": "thinking", "data": {}}
    prior_code = None
    execution_error = None

    for attempt in range(3):
        result = await generate_code(
            question=question,
            schema=schema,
            source_id=session.source_id,
            history_turns=history_turns,
            permitted_tables=permitted_tables,
            prior_code=prior_code,
            execution_error=execution_error,
        )

        await turn_service.update_turn(db, turn.id, thinking=result.thinking)

        if isinstance(result, ClarificationRequest):
            # Classify: if question references unknown table/column → knowledge_gap, else scope
            for q in result.questions:
                if any(kw in q["text"].lower() for kw in ["define", "mean", "what is", "how is"]):
                    await gap_service.record_gap_signal(db, session.source_id, q["text"])

            await turn_service.update_turn(db, turn.id, result_type=TurnResultType.clarification)
            yield {"event": "clarifying", "data": {"questions": result.questions, "turn_id": str(turn.id)}}
            return

        assert isinstance(result, GeneratedCode)
        code = result.code

        # Safety scan
        blocked = scan_dangerous_patterns(code)
        if blocked:
            await AuditService.log(db, AuditEventType.code_blocked, user_id=user_id,
                                   source_id=session.source_id,
                                   details={"reason": "dangerous_pattern", "pattern": blocked})
            await turn_service.update_turn(db, turn.id, result_type=TurnResultType.error)
            yield {"event": "error", "data": {"message": f"Generated code was rejected for security reasons."}}
            return

        # Table permission check
        violated = validate_table_permissions(code, permitted_tables)
        if violated:
            await AuditService.log(db, AuditEventType.code_blocked, user_id=user_id,
                                   source_id=session.source_id,
                                   details={"reason": "table_permission", "table": violated})
            yield {"event": "error", "data": {"message": f"Generated code attempted to access restricted data."}}
            return

        await turn_service.update_turn(db, turn.id, generated_code=code)
        await AuditService.log(db, AuditEventType.code_generated, user_id=user_id, source_id=session.source_id)

        # --- Execution ---
        yield {"event": "executing", "data": {"attempt": attempt + 1}}

        source = await dsm.get_source(session.source_id)
        ds_config = decrypt_config(source.connection_config) if source else {}

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{settings.execution_service_url}/execute",
                    json={"code": code, "data_source_config": ds_config},
                )
            exec_result = resp.json()
        except Exception as e:
            execution_error = str(e)
            prior_code = code
            continue

        if exec_result["type"] == "error":
            execution_error = exec_result["error"]
            prior_code = code
            if attempt == 2:
                await turn_service.update_turn(db, turn.id, result_type=TurnResultType.error)
                await AuditService.log(db, AuditEventType.query_failed, user_id=user_id, source_id=session.source_id)
                yield {"event": "error", "data": {"message": execution_error, "error_type": exec_result.get("error_type")}}
                return
            continue  # retry

        # Success
        result_type = TurnResultType.chart if exec_result["type"] == "chart" else (
            TurnResultType.table if exec_result["type"] == "table" else TurnResultType.empty
        )
        await turn_service.update_turn(
            db, turn.id,
            result_cache=exec_result,
            result_type=result_type,
        )
        await session_service.touch_session(db, session_id)

        # Auto-title session from first question
        if len(prior_turns) == 0:
            title = question[:50] + ("…" if len(question) > 50 else "")
            await session_service.rename_session(db, session_id, user_id, title)

        await AuditService.log(db, AuditEventType.query_completed, user_id=user_id, source_id=session.source_id)
        yield {"event": "done", "data": {"turn_id": str(turn.id), "result": exec_result}}
        return

    # All retries exhausted
    yield {"event": "error", "data": {"message": execution_error or "Execution failed after 3 attempts"}}


async def refresh_turn(db, turn_id: uuid.UUID, user_id: uuid.UUID, session_id: uuid.UUID) -> dict:
    """Re-execute stored code without a new LLM call."""
    turn = await turn_service.get_turn(db, turn_id)
    if not turn or not turn.generated_code:
        return {"type": "error", "error": "No stored code for this turn", "error_type": "runtime"}

    session = await session_service.get_session(db, session_id, user_id)
    if not session:
        return {"type": "error", "error": "Session not found", "error_type": "runtime"}

    dsm = DataSourceManager(db)
    source = await dsm.get_source(session.source_id)
    ds_config = decrypt_config(source.connection_config) if source else {}

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{settings.execution_service_url}/execute",
                json={"code": turn.generated_code, "data_source_config": ds_config},
            )
        exec_result = resp.json()
    except Exception as e:
        return {"type": "error", "error": str(e), "error_type": "runtime"}

    if exec_result["type"] != "error":
        result_type = TurnResultType.chart if exec_result["type"] == "chart" else TurnResultType.table
        await turn_service.update_turn(db, turn_id, result_cache=exec_result, result_type=result_type)

    return exec_result
