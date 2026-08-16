"""SocketIO 事件处理：连接鉴权、房间生命周期、出牌驱动（真人+AI）、倒计时、结算广播。"""

import asyncio
import logging

import socketio

from app import config, security
from app.comment_manager import make_commentator
from app.db import SessionLocal
from app.dz_ai_factory import build_ai
from app.models import AuthToken, User
from app.rooms import Room, RoomManager, _norm_ai_type
from dzcore import dou_dz_adapter as dz
from dzcore.game import Game

logger = logging.getLogger("tricard.ws")
if not logger.handlers:
    _sh = logging.StreamHandler()
    _sh.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    logger.addHandler(_sh)
    logger.setLevel(logging.INFO)
    logger.propagate = False

room_manager = RoomManager()

_USER_BY_SID: dict[str, dict] = {}
_ADDR_BY_SID: dict[str, tuple] = {}
_ROOM_TASKS: dict[str, asyncio.Task] = {}


def _token_user(auth) -> dict | None:
    try:
        token = (auth or {}).get("token", "")
        if not token:
            return None
        with SessionLocal() as db:
            rec = db.query(AuthToken).filter(AuthToken.token_hash == security.hash_token(token)).first()
            if rec is None:
                return None
            u = db.get(User, rec.user_id)
            return u.public() if u else None
    except Exception:  # noqa: BLE001
        return None


def _room_name(code: str) -> str:
    return f"room:{code}"


async def _emit_to_room(sio, event: str, data, room: Room) -> None:
    await sio.emit(event, data, to=_room_name(room.code))


async def _broadcast_room(sio, room: Room) -> None:
    for seat_idx, seat in enumerate(room.seats):
        if seat and seat.connected and seat.sid:
            snap = room.private_snapshot(seat_idx) if room.game else None
            await sio.emit("room_state", {"room": room.public_snapshot(), "private": snap}, to=seat.sid)
    await sio.emit("board", room.public_snapshot(), to=_room_name(room.code))


def register_handlers(sio: socketio.AsyncServer) -> None:
    @sio.event
    async def connect(sid, environ, auth):
        user = _token_user(auth)
        if user is None:
            return False
        _USER_BY_SID[sid] = user
        # 断线重连恢复：若 username 已在一房间，重新绑定 sid 并推送最新状态
        for room in room_manager._rooms.values():
            idx = room.seat_of(user["username"])
            if idx is not None:
                room.seats[idx].connected = True
                room.seats[idx].sid = sid
                _ADDR_BY_SID[sid] = (room.code, idx)
                await sio.enter_room(sid, _room_name(room.code))
                await sio.emit("room_state", {"room": room.public_snapshot(), "private": room.private_snapshot(idx) if room.game else None}, to=sid)
                break
        return True

    @sio.event
    async def disconnect(sid):
        meta = _ADDR_BY_SID.pop(sid, None)
        user = _USER_BY_SID.pop(sid, None)
        if meta and user:
            code, _seat = meta
            room = room_manager.get(code)
            if room:
                room.set_connected(user["username"], False)

    @sio.event
    async def create_room(sid, data):
        user = _USER_BY_SID.get(sid)
        if not user:
            return await sio.emit("error", {"msg": "未登录"}, to=sid)
        base_bet = int((data or {}).get("base_bet", 200))
        ai_type = _norm_ai_type((data or {}).get("ai_type", "basic"))
        room = room_manager.create(user, base_bet=base_bet, ai_type=ai_type)
        _ADDR_BY_SID[sid] = (room.code, 0)
        room.seats[0].sid = sid
        room.seats[0].connected = True
        await sio.enter_room(sid, _room_name(room.code))
        await _broadcast_room(sio, room)

    @sio.event
    async def join_room(sid, data):
        user = _USER_BY_SID.get(sid)
        code = (data or {}).get("code", "")
        room = room_manager.get(str(code))
        if not room:
            return await sio.emit("error", {"msg": "房间不存在"}, to=sid)
        if room.status == "playing":
            return await sio.emit("error", {"msg": "游戏中，暂不能加入"}, to=sid)
        seat = room.add_human(user)
        if seat is None:
            return await sio.emit("error", {"msg": "房间已满"}, to=sid)
        idx = room.seat_of(user["username"])
        _ADDR_BY_SID[sid] = (code, idx)
        room.seats[idx].sid = sid
        room.seats[idx].connected = True
        await sio.enter_room(sid, _room_name(code))
        await _broadcast_room(sio, room)

    @sio.event
    async def leave_room(sid):
        meta = _ADDR_BY_SID.pop(sid, None)
        user = _USER_BY_SID.get(sid)
        if not meta:
            return
        code, _ = meta
        room = room_manager.get(code)
        if room and room.status == "waiting":
            if user and room.seat_of(user["username"]) is not None:
                room.seats = [None if s is not None and s.username == user["username"] else s for s in room.seats]
                if not room.seats[room.host_seat].connected:
                    room_manager.remove(code)
                else:
                    room.fill_ai_seats()
                    await _broadcast_room(sio, room)

    @sio.event
    async def set_ready(sid, data):
        user = _USER_BY_SID.get(sid)
        meta = _ADDR_BY_SID.get(sid)
        if not user or not meta:
            return
        room = room_manager.get(meta[0])
        if room:
            room.set_ready(user["username"], bool((data or {}).get("ready")))
            await _broadcast_room(sio, room)

    @sio.event
    async def start(sid, data):
        user = _USER_BY_SID.get(sid)
        meta = _ADDR_BY_SID.get(sid)
        if not user or not meta:
            return
        room = room_manager.get(meta[0])
        if not room:
            return
        ok, msg = room.can_start(user["username"])
        if not ok:
            return await sio.emit("error", {"msg": msg}, to=sid)
        await _begin_game(sio, room)

    @sio.on("pass")
    async def do_pass(sid, data):
        meta = _ADDR_BY_SID.get(sid)
        user = _USER_BY_SID.get(sid)
        if not meta or not user:
            return
        room = room_manager.get(meta[0])
        if not room or not room.game:
            return
        seat = room.seat_of(user["username"])
        if not room.game.can_pass(seat):
            return await sio.emit("error", {"msg": "当前不能过"}, to=sid)
        room.game.do_pass(seat)
        await sio.emit("ok", {"action": "pass"}, to=sid)
        _signal_turn(room)

    @sio.event
    async def play(sid, data):
        meta = _ADDR_BY_SID.get(sid)
        user = _USER_BY_SID.get(sid)
        if not meta or not user:
            return
        room = room_manager.get(meta[0])
        if not room or not room.game:
            return
        seat = room.seat_of(user["username"])
        cards = (data or {}).get("hand", [])
        if not room.game.can_play(seat, cards):
            return await sio.emit("error", {"msg": "非法出牌"}, to=sid)
        room.game.play(seat, cards)
        await sio.emit("ok", {"action": "play"}, to=sid)
        _signal_turn(room)

    @sio.event
    async def bid(sid, data):
        meta = _ADDR_BY_SID.get(sid)
        user = _USER_BY_SID.get(sid)
        if not meta or not user:
            return
        room = room_manager.get(meta[0])
        if not room or not room.game:
            return
        if room.game.status != "bidding":
            return await sio.emit("error", {"msg": "当前不在叫牌阶段"}, to=sid)
        seat = room.seat_of(user["username"])
        action = (data or {}).get("action", "")
        ok = room.game.bid(seat, action)
        if not ok:
            return await sio.emit("error", {"msg": "非法叫牌"}, to=sid)
        await sio.emit("ok", {"action": "bid"}, to=sid)
        _signal_turn(room)
        await _broadcast_room(sio, room)
        if room.game.status == "playing":
            _ROOM_TASKS[room.code] = asyncio.create_task(_turn_loop(sio, room))


def _signal_turn(room) -> None:
    ev = getattr(room, "turn_event", None)
    if ev and not ev.is_set():
        ev.set()


async def _begin_game(sio, room: Room) -> None:
    try:
        room.fill_ai_seats()
        game = Game()
        game.start()  # enters bidding phase
        room.game = game
        room.status = "playing"
        room.ai_players = {
            i: (None if not seat.is_ai else build_ai(seat.ai_type, seat))
            for i, seat in enumerate(room.seats)
        }
        room.commentator = make_commentator(room, sio)
        # AI 在叫牌阶段自动叫地主/不叫
        _ROOM_TASKS[room.code] = asyncio.create_task(_bidding_loop(sio, room))
        await _broadcast_room(sio, room)
    except Exception:  # noqa: BLE001
        logger.exception("begin_game failed")
        room.status = "waiting"


async def _bidding_loop(sio, room: Room) -> None:
    try:
        while room.game.status == "bidding":
            seat = room.game.bidding_seat
            await _broadcast_room(sio, room)
            if room.seats[seat].is_ai:
                # AI 简单策略：随机叫地主
                import random
                action = "landlord" if random.random() < 0.3 else "pass"
                room.game.bid(seat, action)
            else:
                room.turn_event = asyncio.Event()
                timeout_task = asyncio.create_task(_bid_timeout(sio, room, seat))
                try:
                    await room.turn_event.wait()
                finally:
                    timeout_task.cancel()
                    try:
                        await timeout_task
                    except asyncio.CancelledError:
                        pass
            await _broadcast_room(sio, room)
        if room.game.status == "playing":
            await _turn_loop(sio, room)
    except Exception:  # noqa: BLE001
        logger.exception("bidding_loop crashed")
    finally:
        _ROOM_TASKS.pop(room.code, None)


async def _bid_timeout(sio, room: Room, seat: int) -> None:
    await asyncio.sleep(config.PLAY_TIMEOUT)
    # 超时自动"不叫"
    room.game.bid(seat, "pass")
    _signal_turn(room)


async def _turn_loop(sio, room: Room) -> None:
    try:
        while room.status == "playing":
            g = room.game
            seat = g.turn
            await _broadcast_room(sio, room)
            prev_trick = g.trick_index
            prev_bombs = g.bomb_count

            if room.seats[seat].is_ai:
                await _run_ai(sio, room, seat)
            else:
                room.turn_event = asyncio.Event()
                timeout_task = asyncio.create_task(_human_timeout(sio, room, seat))
                try:
                    await room.turn_event.wait()
                finally:
                    timeout_task.cancel()
                    try:
                        await timeout_task
                    except asyncio.CancelledError:
                        pass

            if room.commentator and g.status == "playing" and (g.trick_index != prev_trick or g.bomb_count != prev_bombs):
                room.commentator.maybe_comment(g)

            if g.status == "finished":
                await _finish_room(sio, room)
                return
    except Exception:  # noqa: BLE001
        logger.exception("turn_loop crashed in room %s", room.code)
    finally:
        _ROOM_TASKS.pop(room.code, None)


async def _run_ai(sio, room: Room, seat: int) -> None:
    ai = room.ai_players[seat]
    g = room.game
    ctx = {"game": g}
    t0 = __import__("time").time()
    try:
        move = await asyncio.wait_for(
            asyncio.to_thread(_ai_call, ai, g, seat, ctx),
            timeout=config.PLAY_TIMEOUT,
        )
    except asyncio.TimeoutError:
        move = g.timeout_action(seat)
    elapsed = __import__("time").time() - t0
    # AI 出牌太快时至少等 3s，让玩家有反应时间
    wait = max(0, 3.0 - elapsed)
    if wait > 0:
        await asyncio.sleep(wait)
    if move is None:
        g.do_pass(seat)
    else:
        g.play(seat, move)


def _ai_call(ai, g, seat, ctx):
    if ai is None:
        return g.timeout_action(seat)
    return ai.choose_action(g.hands[seat], g.last_play, ctx)


async def _human_timeout(sio, room: Room, seat: int) -> None:
    await asyncio.sleep(config.PLAY_TIMEOUT)
    g = room.game
    if room.status == "playing" and g.turn == seat:
        move = g.timeout_action(seat)
        if move is None:
            g.do_pass(seat)
        else:
            g.play(seat, move)
        await sio.emit("timed_out", {"seat": seat}, to=_room_name(room.code))
        _signal_turn(room)


async def _finish_room(sio, room: Room) -> None:
    result = room.settle()
    # 落库
    with SessionLocal() as db:
        for seat in room.seats:
            u = db.query(User).filter(User.id == seat.user_id).first()
            if u:
                info = result["per_seat"][room.seat_of(seat.username)]
                u.joy_beans += info["delta"]
                u.wins += 1 if info["won"] else 0
                u.losses += 0 if info["won"] else 1
        db.commit()

    room.status = "finished"
    await sio.emit("game_end", {"result": result}, to=_room_name(room.code))
    await _broadcast_room(sio, room)

    await asyncio.sleep(1.5)
    if room.status == "finished":
        room.status = "waiting"
        for s in room.seats:
            if s and not s.is_ai:
                s.ready = False
        room.game = None
        room.ai_players = {}
        room.commentator = None
        room.turn_event = asyncio.Event()
        await _broadcast_room(sio, room)