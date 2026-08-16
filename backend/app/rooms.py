"""房间管理：创建/加入/就绪/开始/AI 填充/状态快照。纯逻辑、可同步测试。"""

import random
from dataclasses import dataclass, field

from app import config
from app.beans import settle_by_players
from dzcore import dou_dz_adapter as dz
from dzcore.game import Game

AI_TYPES = ("basic", "douzero", "llm")
PERSONALITIES = ("off", "kind", "savage", "chatterbox")


def _norm_ai_type(t: str) -> str:
    return t if t in AI_TYPES else "basic"


@dataclass
class Seat:
    user_id: int
    username: str
    nickname: str
    avatar: str | None = None
    is_ai: bool = False
    ai_type: str = "basic"          # AI 时：basic/douzero/llm
    personality: str = "savage"     # AI 评论人格（off 关闭）
    ready: bool = False             # AI 视为自动就绪
    connected: bool = False
    sid: str | None = None          # socketio session id（真人）

    def to_public(self) -> dict:
        return {
            "nickname": self.nickname,
            "username": self.username,
            "avatar": self.avatar,
            "is_ai": self.is_ai,
            "ai_type": self.ai_type if self.is_ai else None,
            "personality": self.personality if self.is_ai else None,
            "ready": self.ready,
            "connected": self.connected or self.is_ai,
        }


@dataclass
class Room:
    code: str
    host_seat: int
    base_bet: int = 200
    seats: list[Seat | None] = field(default_factory=lambda: [None, None, None])
    status: str = "waiting"          # waiting / playing / finished
    game: Game | None = None

    def seat_of(self, username: str) -> int | None:
        for i, s in enumerate(self.seats):
            if s and s.username == username:
                return i
        return None

    def is_host(self, username: str) -> bool:
        s = self.seats[self.host_seat]
        return s is not None and s.username == username

    def add_human(self, user) -> Seat | None:
        """真人入座：优先空位；没有空位则顶替一个 AI 座位。返回座位或 None(满)。"""
        s = self.seat_of(user["username"])
        if s is not None:
            self.seats[s].connected = True
            return self.seats[s]
        for i in range(3):
            if self.seats[i] is None:
                seat = Seat(user_id=user["id"], username=user["username"], nickname=user["nickname"], avatar=user.get("avatar"), connected=True)
                self.seats[i] = seat
                return seat
        # 顶替第一个 AI
        for i in range(3):
            if self.seats[i].is_ai:
                seat = Seat(user_id=user["id"], username=user["username"], nickname=user["nickname"], avatar=user.get("avatar"), connected=True)
                self.seats[i] = seat
                return seat
        return None

    def set_connected(self, username: str, connected: bool, sid: str | None = None) -> None:
        i = self.seat_of(username)
        if i is not None:
            self.seats[i].connected = connected
            self.seats[i].sid = sid if connected else None

    def set_ready(self, username: str, ready: bool) -> None:
        i = self.seat_of(username)
        if i is not None and not self.seats[i].is_ai:
            self.seats[i].ready = ready

    def all_humans_ready(self) -> bool:
        humans = [s for s in self.seats if s and not s.is_ai]
        return all(s.ready for s in humans) if humans else True

    def can_start(self, host_username: str) -> tuple[bool, str]:
        n = len([s for s in self.seats if s])
        if n < 3:
            return False, "座位未坐满（空位将自动由 AI 填充后再开）"
        if not self.is_host(host_username):
            return False, "只有房主可以开始"
        if not self.all_humans_ready():
            return False, "还有真人未准备"
        return True, ""

    def fill_ai_seats(self, ai_type: str | None = None) -> None:
        """空位补 AI。AI 座位自动 ready。"""
        ai_type = _norm_ai_type(ai_type or getattr(self, "default_ai_type", config.AI_DEFAULT_TYPE))
        ai_index = 0
        for i in range(3):
            if self.seats[i] is None:
                self.seats[i] = Seat(
                    user_id=-1000 - ai_index, username=f"ai_fill_{i}", nickname=f"AI伙伴{ai_index+1}",
                    is_ai=True, ai_type=ai_type, personality="savage", ready=True,
                )
                ai_index += 1
        for s in self.seats:
            if s and s.is_ai:
                s.ready = True

    def public_snapshot(self) -> dict:
        return {
            "code": self.code,
            "host_seat": self.host_seat,
            "base_bet": self.base_bet,
            "status": self.status,
            "seats": [s.to_public() if s else None for s in self.seats],
            "players": len([s for s in self.seats if s]),
            "those_ready": [s.nickname for s in self.seats if s and s.ready],
        }

    def private_snapshot(self, seat_idx: int) -> dict:
        g = self.game
        if g is None:
            return {"status": "waiting"}
        b = {
            "status": g.status,
            "turn": g.turn if g else None,
            "last_play": [c for c in g.last_play] if g and g.last_play else [],
            "last_play_labels": dz.cards_label(g.last_play) if g and g.last_play else [],
            "last_play_by": g.last_play_seat if g else None,
            "trick": g.trick_index if g else 0,
            "bomb_count": g.bomb_count if g else 0,
            "hand": [c for c in g.hands[seat_idx]] if g else [],
            "hand_labels": dz.cards_label(g.hands[seat_idx]) if g else [],
            "remaining": [g.hand_size(i) for i in range(3)] if g else [0, 0, 0],
            "landlord_seat": g.landlord_seat if g else None,
            "bottom": dz.cards_label(g.bottom) if g and g.status == "playing" else [],
            "can_act": bool(g and g.turn == seat_idx),
            "history": [{"seat": e["seat"], "action": e["action"], "labels": e["labels"], "trick": e["trick"]} for e in (g.history or [])],
        }
        # 抢地主阶段
        if g.status == "bidding":
            b["bidding_seat"] = g.bidding_seat
            b["bidders"] = g.bidders
            b["can_bid"] = g.bidding_seat == seat_idx
        # 是否能压住上家
        if g.last_play and g.turn == seat_idx:
            b["can_beat_any"] = len(dz.list_beating(g.last_play, g.hands[seat_idx])) > 0
        else:
            b["can_beat_any"] = True
        return b

    # ---- 结算 ----
    def settle(self) -> dict:
        g = self.game
        names = [s.nickname for s in self.seats]
        landlord_win = g.winner_team == "landlord"
        deltas = settle_by_players(
            names, g.landlord_seat, self.base_bet, g.bomb_count, g.spring, landlord_win
        )
        # 输赢 & 战绩
        per_seat = {}
        for i, s in enumerate(self.seats):
            is_landlord = i == g.landlord_seat
            won = (landlord_win and is_landlord) or (not landlord_win and not is_landlord)
            per_seat[i] = {
                "nickname": s.nickname,
                "delta": deltas[s.nickname],
                "won": won,
                "team": "landlord" if is_landlord else "farmers",
            }
        return {
            "winner_team": g.winner_team,
            "winner_seat": g.winner_seat,
            "bombs": g.bomb_count,
            "spring": g.spring,
            "multiplier": deltas,
            "per_seat": per_seat,
        }


class RoomManager:
    def __init__(self):
        self._rooms: dict[str, Room] = {}
        self._used: set[str] = set()

    def _gen_code(self) -> str:
        for _ in range(1000):
            code = str(random.randrange(100000, 1000000))
            if code not in self._used:
                self._used.add(code)
                return code
        raise RuntimeError("code space exhausted")

    def create(self, host_user: dict, base_bet: int = 200, ai_type: str = "basic", personality: str = "savage") -> Room:
        code = self._gen_code()
        host = Seat(user_id=host_user["id"], username=host_user["username"], nickname=host_user["nickname"],
                    avatar=host_user.get("avatar"), connected=True, ready=True)  # 房主自动就绪
        room = Room(code=code, host_seat=0, base_bet=base_bet, seats=[host, None, None])
        room.default_ai_type = _norm_ai_type(ai_type)
        room.fill_ai_seats(room.default_ai_type)
        self._rooms[code] = room
        return room

    def get(self, code: str) -> Room | None:
        return self._rooms.get(code)

    def remove(self, code: str) -> None:
        self._rooms.pop(code, None)
        self._used.discard(code)

    def list_rooms(self) -> list[dict]:
        return [r.public_snapshot() for r in self._rooms.values() if r.status != "playing"]