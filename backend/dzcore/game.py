"""斗地主对局状态机：发牌/叫地主/出牌轮转/胜负判定。服务端权威。"""

import logging
import random
import time
from collections import Counter

from . import dou_dz_adapter as dz

logger = logging.getLogger("tricard.game")


class Game:
    STATUS_IDLE = "idle"
    STATUS_BIDDING = "bidding"
    STATUS_PLAYING = "playing"
    STATUS_FINISHED = "finished"

    def __init__(self):
        self.hands: list[list[int]] = [[], [], []]
        self.bottom: list[int] = []
        self.landlord_seat: int | None = None
        self.turn: int | None = None
        self.status: str = self.STATUS_IDLE

        self.last_play: list[int] = []
        self.last_play_seat: int | None = None
        self.pass_count: int = 0
        self.trick_index: int = 0
        self.bomb_count: int = 0

        self.history: list[dict] = []
        self.winner_team: str | None = None  # "landlord" | "farmers"
        self.winner_seat: int | None = None
        self.spring: bool = False

        self.bidders: list[bool] = [False, False, False]  # 每人是否叫过地主
        self.bidding_seat: int = 0
        self.last_bid: int | None = None  # 最后一个叫地主的座位

        self.listeners: list[callable] = []
        self._turn_start: float | None = None  # 当前回合开始时间
        self._log_entries: list[str] = []

    def _log(self, msg: str) -> None:
        logger.info(msg)
        self._log_entries.append(msg)

    def _log_move(self, seat: int, action: str, cards_str: str) -> None:
        thinking = ""
        if self._turn_start is not None:
            elapsed = time.time() - self._turn_start
            thinking = f" thinking={elapsed:.2f}s"
        self._log(
            f"[trick={self.trick_index}] seat={seat} {action} {cards_str}{thinking}"
        )

    # ---------------------------------------------------------------- setup

    def start(self, seed: int | None = None) -> None:
        """发牌并进入抢地主阶段。"""
        if seed is not None:
            random.seed(seed)
        hands, bottom = dz.deal()
        self.hands = hands
        self.bottom = bottom
        self.status = self.STATUS_BIDDING
        self.bidding_seat = 0
        self.bidders = [False, False, False]
        self.last_bid = None
        self._emit("bidding_start")

    def start_quick(self, seed: int | None = None) -> None:
        """发牌直接分配地主（跳过抢地主）。用于测试/模拟。"""
        if seed is not None:
            random.seed(seed)
        hands, bottom = dz.deal()
        self.hands = hands
        self.bottom = bottom
        self.landlord_seat = random.randrange(3)
        self.hands[self.landlord_seat] = dz.sort_cards(self.hands[self.landlord_seat] + bottom)
        self.turn = self.landlord_seat
        self.status = self.STATUS_PLAYING
        self.trick_index = 1
        self._turn_start = time.time()
        self._emit("game_start", landlord=self.landlord_seat, bottom=dz.cards_label(bottom))

    def bid(self, seat: int, action: str) -> bool:
        """叫地主：action='landlord'|'pass'。返回 True 表示有效。"""
        if self.status != self.STATUS_BIDDING or seat != self.bidding_seat:
            return False
        self._log(f"[bid] seat={seat} action={action}")
        if action == "landlord":
            self.last_bid = seat
            self.landlord_seat = seat
            self.bidders[seat] = True
            # 有人叫地主，立即结束叫牌
            self._finish_bidding()
            return True
        elif action == "pass":
            self.bidders[seat] = True
            # 轮到下一个人
            next_seat = (seat + 1) % 3
            # 如果所有人都过了（三人都 pass），最后一人强制为地主
            if all(self.bidders):
                self.landlord_seat = next_seat  # 最后一个玩家强制地主
                self._finish_bidding()
            else:
                self.bidding_seat = next_seat
                self._emit("bid_turn", seat=self.bidding_seat)
            return True
        return False

    def _finish_bidding(self) -> None:
        self._log(f"[bidding_end] landlord={self.landlord_seat}")
        # 底牌并入地主手牌
        self.hands[self.landlord_seat] = dz.sort_cards(self.hands[self.landlord_seat] + self.bottom)
        self.turn = self.landlord_seat
        self.status = self.STATUS_PLAYING
        self.trick_index = 1
        self._emit("game_start", landlord=self.landlord_seat, bottom=dz.cards_label(self.bottom))

    def prime(self, hands: list[list[int]], bottom: list[int], landlord_seat: int, turn: int) -> None:
        """测试/残局用：注入固定局面。"""
        self.hands = [dz.sort_cards(h) for h in hands]
        self.bottom = bottom
        self.landlord_seat = landlord_seat
        self.turn = turn
        self.status = self.STATUS_PLAYING
        self.trick_index = 1

    # ---------------------------------------------------------------- queries

    def is_farmer(self, seat: int) -> bool:
        return seat != self.landlord_seat

    def team_of(self, seat: int) -> str:
        return "landlord" if seat == self.landlord_seat else "farmers"

    def hand_size(self, seat: int) -> int:
        return len(self.hands[seat])

    def can_pass(self, seat: int) -> bool:
        """出可不出时才能过：只有上家领先过时才轮到、（即 last_play 非空）才能过。"""
        return bool(self.last_play)

    def can_play(self, seat: int, cards: list[int]) -> bool:
        if self.status != self.STATUS_PLAYING or seat != self.turn:
            return False
        if not cards:
            return self.can_pass(seat)
        if not dz.has_cards(self.hands[seat], cards):
            return False
        return dz.can_beat(cards, self.last_play)

    # ---------------------------------------------------------------- actions

    def play(self, seat: int, cards: list[int]) -> bool:
        if not self.can_play(seat, cards):
            return False
        is_bomb = dz.count_bomb_rocket(cards)
        if is_bomb:
            self.bomb_count += 1
        # 移出手牌
        hand_counter = Counter(self.hands[seat])
        hand_counter.subtract(cards)
        self.hands[seat] = dz.sort_cards(list(hand_counter.elements()))

        self._log_move(seat, "play", " ".join(dz.cards_label(cards)))
        self._record(seat, "play", cards)
        self.last_play = list(cards)
        self.last_play_seat = seat
        self.pass_count = 0
        self._emit("play", seat=seat, cards=dz.cards_label(cards), bomb=is_bomb)

        if not self.hands[seat]:
            self._finish(seat)
            return True
        self._advance()
        return True

    def do_pass(self, seat: int) -> bool:
        if not self.can_pass(seat):
            return False
        self._log_move(seat, "pass", "")
        self._record(seat, "pass", [])
        self.pass_count += 1
        self._emit("pass", seat=seat)
        if self.pass_count >= 2:
            # 一轮结束：新一轮由本轮胜者领出
            self.last_play = []
            self.pass_count = 0
            self.turn = self.last_play_seat
            self.trick_index += 1
            self._emit("trick_end", winner=self.last_play_seat)
            return True
        self._advance()
        return True

    def timeout_action(self, seat: int) -> list[int] | None:
        """超时兜底：领出→最小合法牌；否则→过（由调用方执行 do_pass）。"""
        if self.can_pass(seat):
            return None
        return dz.minimal_lead(self.hands[seat])

    # ---------------------------------------------------------------- internal

    def _advance(self) -> None:
        self.turn = (self.turn + 1) % 3
        self._turn_start = time.time()

    def _record(self, seat: int, action: str, cards: list[int]) -> None:
        self.history.append(
            {
                "seat": seat,
                "action": action,
                "cards": list(cards),
                "labels": dz.cards_label(cards),
                "trick": self.trick_index,
                "hand_left": self.hand_size(seat),
            }
        )

    def _finish(self, seat: int) -> None:
        self._log(f"[game_end] winner_seat={seat} team={self.team_of(seat)}")
        self.status = self.STATUS_FINISHED
        self.winner_seat = seat
        self.winner_team = self.team_of(seat)
        # 春天/反春：一方出完时，另一方（们）一张都没打出过
        landlord_played = any(e["action"] == "play" and e["seat"] == self.landlord_seat for e in self.history)
        farmer_played = any(e["action"] == "play" and e["seat"] != self.landlord_seat for e in self.history)
        if self.winner_team == "landlord":
            self.spring = not farmer_played
        else:
            self.spring = not landlord_played
        self._emit("game_end", winner=seat, team=self.winner_team, bombs=self.bomb_count, spring=self.spring)

    def _emit(self, event: str, **kw) -> None:
        for fn in self.listeners:
            try:
                fn({"type": event, **kw})
            except Exception:  # noqa: BLE001
                pass

    def add_listener(self, fn: callable) -> None:
        self.listeners.append(fn)


def new_standard_game(seed: int | None = None) -> Game:
    g = Game()
    g.start_quick(seed=seed)
    return g