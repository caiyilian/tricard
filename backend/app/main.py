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
from app.socketio_routes import register_handlers
from app.users import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
register_handlers(sio)

app = FastAPI(title="tricard", version="0.3.0", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(ranking_router)
app.mount("/avatars", StaticFiles(directory=config.AVATAR_DIR), name="avatars")

# 前端静态文件（生产构建）
_frontend = config.BACKEND_DIR.parent / "frontend" / "dist"
if _frontend.exists():
    app.mount("/", StaticFiles(directory=str(_frontend), html=True), name="frontend")


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "tricard",
        "api_keys": len(config.SENSENOVA_API_KEYS),
        "model": config.SENSENOVA_MODEL,
    }


@app.get("/api/rooms")
async def rooms_list():
    from app.socketio_routes import room_manager

    return {"rooms": room_manager.list_rooms()}


sio_app = socketio.ASGIApp(sio, other_asgi_app=app)