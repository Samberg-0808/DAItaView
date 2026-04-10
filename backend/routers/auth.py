from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db import get_db
from backend.dependencies import get_current_user
from backend.models.user import User
from backend.services.audit_service import AuditService
from backend.models.audit import AuditEventType
from backend.services.auth_service import authenticate_user, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, body.username, body.password)
    if not user:
        await AuditService.log(db, AuditEventType.login_failed, details={"username": body.username})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(user.id, user.role)
    await AuditService.log(db, AuditEventType.login_success, user_id=user.id)
    return TokenResponse(access_token=token)


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await AuditService.log(db, AuditEventType.logout, user_id=current_user.id)
    return {"detail": "Logged out"}


@router.get("/sso/redirect")
async def sso_redirect():
    if settings.auth_mode == "local":
        raise HTTPException(status_code=400, detail="SSO not configured")
    # SSO redirect URL built by authlib — wired in main.py via OAuth client
    return {"detail": "SSO redirect not yet configured — set AUTH_MODE and SSO_* env vars"}
