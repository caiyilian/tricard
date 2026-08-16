"""斗地主对局状态机：发牌/叫地主/出牌轮转/胜负判定。服务端权威。"""

import random
from collections import Counter

from . import dou_dz_adapter as dz


class Game:
    STATUS_IDLE = "idle"
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

        self.listeners: list[callable] = []

    # ---------------------------------------------------------------- setup

    def start(self, seed: int | None = None) -> None:
        """发牌并随机指定地主，地主先出。"""
        if seed is not None:
            random.seed(seed)
        hands, bottom = dz.deal()
        self.hands = hands
        self.bottom = bottom
        self.landlord_seat = random.randrange(3)
        # 底牌并入地主手牌
        self.hands[self.landlord_seat] = dz.sort_cards(self.hands[self.landlord_seat] + bottom)
        self.turn = self.landlord_seat
        self.status = self.STATUS_PLAYING
        self.trick_index = 1
        self._emit("game_start", landlord=self.landlord_seat, bottom=dz.cards_label(bottom))

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
        self.status = self.STATUS_FINISHED
        self.winner_seat = seat
        self.winner_team = self.team_of(seat)
        self._emit("game_end", winner=seat, team=self.winner_team, bombs=self.bomb_count)

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
    g.start(seed=seed)
    return g