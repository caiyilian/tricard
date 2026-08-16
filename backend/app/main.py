"""FastAPI + SocketIO entry point (Phase 0: health + socketio handshake)."""

import socketio
from fastapi import FastAPI

from app import config

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")

app = FastAPI(title="tricard", version="0.1.0")
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


# 供 uvicorn --app-dir backend 使用：uvicorn app.main:sio_app
# 或直接：uvicorn app.main:app （此时 /socket.io 不注册，仅 HTTP）