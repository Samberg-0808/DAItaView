import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_db
from backend.dependencies import get_current_user
from backend.models.user import User
from backend.services import session_service, turn_service
from backend.services.query_pipeline import refresh_turn, stream_turn

router = APIRouter(prefix="/sessions", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    source_id: uuid.UUID


class PatchSessionRequest(BaseModel):
    title: str | None = None
    is_pinned: bool | None = None


@router.post("")
async def create_session(
    body: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await session_service.create_session(db, current_user.id, body.source_id)


@router.get("")
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await session_service.list_sessions(db, current_user.id)


@router.get("/{session_id}")
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await session_service.get_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.patch("/{session_id}")
async def patch_session(
    session_id: uuid.UUID,
    body: PatchSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.title is not None:
        await session_service.rename_session(db, session_id, current_user.id, body.title)
    if body.is_pinned is not None:
        await session_service.pin_session(db, session_id, current_user.id, body.is_pinned)
    return await session_service.get_session(db, session_id, current_user.id)


@router.delete("/{session_id}")
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await session_service.delete_session(db, session_id, current_user.id)
    return {"detail": "Session deleted"}


@router.get("/{session_id}/turns")
async def get_turns(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await session_service.get_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return await turn_service.get_turns(db, session_id)


@router.post("/{session_id}/turns/{turn_id}/refresh")
async def refresh_turn_endpoint(
    session_id: uuid.UUID,
    turn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await refresh_turn(db, turn_id, current_user.id, session_id)


@router.post("/{session_id}/refresh")
async def refresh_all(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    turns = await turn_service.get_turns(db, session_id)
    results = []
    for turn in turns:
        if turn.generated_code:
            r = await refresh_turn(db, turn.id, current_user.id, session_id)
            results.append({"turn_id": str(turn.id), "result": r})
    return results


@router.websocket("/{session_id}/query")
async def websocket_query(
    session_id: uuid.UUID,
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db),
):
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            payload = json.loads(raw)
            question = payload.get("question", "").strip()
            clarification_answers = payload.get("clarification_answers")
            token = payload.get("token", "")

            if not question:
                await websocket.send_json({"event": "error", "data": {"message": "Question cannot be empty"}})
                continue

            # Validate JWT from payload (WebSocket can't use header-based auth easily)
            from backend.services.auth_service import decode_token, get_user_by_id
            token_data = decode_token(token)
            if not token_data:
                await websocket.send_json({"event": "error", "data": {"message": "Unauthorized"}})
                continue
            import uuid as _uuid
            user = await get_user_by_id(db, _uuid.UUID(token_data["sub"]))
            if not user:
                await websocket.send_json({"event": "error", "data": {"message": "User not found"}})
                continue

            async for event in stream_turn(db, session_id, user.id, question, clarification_answers):
                await websocket.send_json(event)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"event": "error", "data": {"message": str(e)}})
        except Exception:
            pass
