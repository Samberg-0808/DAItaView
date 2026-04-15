import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db import get_db
from backend.dependencies import get_current_user, require_role
from backend.models.audit import AuditEventType
from backend.models.data_source import DataSourceType
from backend.models.user import User, UserRole
from backend.services.audit_service import AuditService
from backend.services.data_source_manager import DataSourceManager
from backend.services.permission_service import get_permitted_tables

router = APIRouter(prefix="/sources", tags=["data_sources"])

FILE_TYPES = {
    ".csv": DataSourceType.csv,
    ".json": DataSourceType.json,
    ".parquet": DataSourceType.parquet,
}


class ConnectDatabaseRequest(BaseModel):
    name: str
    type: DataSourceType
    host: str = ""
    port: int | None = None
    database: str
    user: str = ""
    password: str = ""


@router.get("")
async def list_sources(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    manager = DataSourceManager(db)
    return await manager.list_sources()


@router.post("")
async def connect_database(
    body: ConnectDatabaseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.super_admin, UserRole.data_admin)),
):
    manager = DataSourceManager(db)
    params = {"host": body.host, "port": body.port, "database": body.database, "user": body.user, "password": body.password}
    try:
        source = await manager.connect_database(body.name, body.type, params, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Connection failed: {e}")
    await AuditService.log(db, AuditEventType.source_connected, user_id=current_user.id, source_id=source.id)
    return source


@router.post("/upload")
async def upload_file(
    name: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.super_admin, UserRole.data_admin)),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in FILE_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {list(FILE_TYPES.keys())}")

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.max_upload_size_mb:
        raise HTTPException(status_code=400, detail=f"File exceeds {settings.max_upload_size_mb}MB limit")

    upload_dir = Path(settings.uploads_path)
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / f"{uuid.uuid4()}{suffix}"
    dest.write_bytes(content)

    manager = DataSourceManager(db)
    source = await manager.connect_file(name, FILE_TYPES[suffix], str(dest), current_user.id)
    await AuditService.log(db, AuditEventType.source_connected, user_id=current_user.id, source_id=source.id)
    return source


@router.get("/{source_id}/schema")
async def get_schema(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    manager = DataSourceManager(db)
    full_schema = await manager.extract_schema(source_id)
    if current_user.role in (UserRole.super_admin, UserRole.data_admin):
        return full_schema
    permitted = await get_permitted_tables(db, current_user.id, source_id)
    if permitted == []:  # empty list = no access
        raise HTTPException(status_code=403, detail="No access to this data source")
    return manager.get_filtered_schema(full_schema, permitted)


@router.post("/{source_id}/refresh-schema")
async def refresh_schema(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.super_admin, UserRole.data_admin)),
):
    manager = DataSourceManager(db)
    schema = await manager.extract_schema(source_id)
    return {"schema": schema, "detail": "Schema refreshed"}


@router.delete("/{source_id}")
async def delete_source(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.super_admin, UserRole.data_admin)),
):
    manager = DataSourceManager(db)
    await manager.delete_source(source_id)
    await AuditService.log(db, AuditEventType.source_deleted, user_id=current_user.id, source_id=source_id)
    return {"detail": "Source deleted"}
