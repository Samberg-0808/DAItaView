from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db import AsyncSessionLocal
from backend.routers import audit, auth, data_sources, groups, knowledge, sessions, users
from backend.services.auth_service import seed_superadmin


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncSessionLocal() as db:
        await seed_superadmin(db)
    yield


app = FastAPI(title="DAItaView API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(groups.router)
app.include_router(data_sources.router)
app.include_router(knowledge.router)
app.include_router(sessions.router)
app.include_router(audit.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
