"""阶段5 验收脚本：N 个模拟客户端真实走 注册→建房→就绪→开局→自动打完整局→结算。

用法：
    # 先启动后端
    uvicorn app.main:sio_app --app-dir backend --host 127.0.0.1 --port 8000
    # 再跑（默认 1 真人 + 2 AI，即自动打一局）
    uv run python backend/scripts/ws_clients.py --players 1
    uv run python backend/scripts/ws_clients.py --players 3
"""

import argparse
import asyncio
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import socketio  # noqa: E402

from dzcore import dou_dz_adapter as dz  # noqa: E402
from dzcore.ai_basic import BasicAI  # noqa: E402

URL = "http://127.0.0.1:8000"
_users = {}


def _http(method, path, payload=None):
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if body else {}
    req = urllib.request.Request(URL + path, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


async def get_token(i: int) -> str:
    name = f"bot_{i}"
    st, data = _http("POST", "/api/auth/register", {"username": name, "password": "pw1234", "nickname": f"联机测试{i}"})
    if st != 200:
        st, data = _http("POST", "/api/auth/login", {"username": name, "password": "pw1234"})
    return data["token"]


async def client(i: int, token: str, ai: BasicAI, box: dict):
    sio = socketio.AsyncClient(logger=False, engineio_logger=False)
    state = {}
    acted_turn_key = None

    @sio.event
    async def room_state(data):
        state["room"] = data.get("room")
        state["priv"] = data.get("private")

    @sio.event
    async def error(data):
        print(f"[p{i}] ERROR: {data}")

    @sio.event
    async def game_end(data):
        print(f"[p{i}] GAME_END: winner={data.get('result',{}).get('winner_team')}")
        state["ended"] = True

    await sio.connect(URL, auth={"token": token}, wait_timeout=10)
    print(f"[p{i}] connected")
    if i == 0:
        await sio.emit("create_room", {"base_bet": 200, "ai_type": "basic"})
        await sio.sleep(0.4)
        box["code"] = state.get("room", {}).get("code")
    else:
        while not box.get("code"):
            await sio.sleep(0.3)
        await sio.emit("join_room", {"code": box["code"]})
        await sio.sleep(0.4)
    await sio.emit("set_ready", {"ready": True})
    await sio.sleep(0.3)
    box["ready_count"] = box.get("ready_count", 0) + 1
    if i == 0:
        # 等所有真人就绪再开局
        for _ in range(200):
            if box.get("ready_count", 0) >= box["players"]:
                break
            await sio.sleep(0.15)
        await sio.emit("start", {})
        print(f"[p{i}] host 开始")

    turns = 0
    while True:
        turns += 1
        if turns > 800:
            print(f"[p{i}] TURN-OVERRUN 未在限制内结束")
            break
        await sio.sleep(0.15)
        room = state.get("room") or {}
        priv = state.get("priv") or {}
        if not room:
            continue
        if state.get("ended"):
            break
        if not room.get("status"):
            continue
        if priv.get("can_act") and room.get("status") == "playing":
            hand = list(priv.get("hand", []))
            last = list(priv.get("last_play", []))
            move = ai.choose_action(hand, last)
            if move is None:
                await sio.emit("pass", {})
                print(f"[p{i}] 过")
            else:
                await sio.emit("play", {"hand": move})
                print(f"[p{i}] 出 {dz.cards_label(move)}")
            state["priv"] = {}  # 防止重复触发
            await sio.sleep(0.2)
        if room.get("status") == "finished":
            # 等结算落库后回 waiting
            await sio.sleep(1.0)
    await sio.disconnect()


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--players", type=int, default=1, choices=[1, 2, 3])
    args = ap.parse_args()
    tokens = [await get_token(i) for i in range(args.players)]
    ais = [BasicAI(name=f"玩家{i}") for i in range(args.players)]
    box: dict = {"players": args.players}
    await asyncio.gather(*(client(i, tokens[i], ais[i], box) for i in range(args.players)))
    print("DONE")


if __name__ == "__main__":
    asyncio.run(main())