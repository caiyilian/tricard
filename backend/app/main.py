"""FastAPI + SocketIO 入口。

启动：uvicorn app.main:sio_app --app-dir backend --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager

import socketio
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import config
from app.auth import router as auth_router
from app.db import init_db
from app.ranking import router as ranking_router
from app.users import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")

app = FastAPI(title="tricard", version="0.2.0", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(ranking_router)
app.mount("/avatars", StaticFiles(directory=config.AVATAR_DIR), name="avatars")

sio_app = socketio.ASGIApp(sio, other_asgi_app=app)


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "tricard",
        "api_keys": len(config.SENSENOVA_API_KEYS),
        "model": config.SENSENOVA_MODEL,
    }


@sio.event
async def connect(sid, environ, auth):
    return True


@sio.event
async def disconnect(sid):
    return


@sio.event
async def ping(sid, data=None):
    await sio.emit("pong", {"echo": data, "time": __import__("time").time()}, to=sid)