"""显著度 & 频控：羞耻/荣誉值累计 + 冷却 + 每轮/每局上限。"""


class FrequencyController:
    """控制整桌评论频率（不刷屏）。"""

    def __init__(self, *, cooldown_turns: int = 3, per_trick_max: int = 1, per_seat_max: int = 3):
        self.cooldown_turns = cooldown_turns       # 两次评论间至少隔 N 个动作
        self.per_trick_max = per_trick_max         # 每轮(回合)最多几条
        self.per_seat_max = per_seat_max           # 每局每个会话最多几条
        self._last_comment_turn = -10**9
        self._trick_comments = 0
        self._cur_trick = None
        self._seat_counts: dict[int, int] = {}
        self._salience: dict[int, int] = {}

    def add_salience(self, target_seat: int, intensity: int) -> None:
        self._salience[target_seat] = self._salience.get(target_seat, 0) + intensity

    def consume(self, target_seat: int) -> int:
        """取走累计显著度并清零。"""
        v = self._salience.pop(target_seat, 0)
        return v

    def can_comment(self, seat: int, turn: int, trick: int) -> bool:
        if self._cur_trick != trick:
            self._cur_trick = trick
            self._trick_comments = 0
        if self._trick_comments >= self.per_trick_max:
            return False
        if turn - self._last_comment_turn < self.cooldown_turns:
            return False
        if self._seat_counts.get(seat, 0) >= self.per_seat_max:
            return False
        return True

    def mark_comment(self, seat: int, turn: int) -> None:
        self._last_comment_turn = turn
        self._trick_comments += 1
        self._seat_counts[seat] = self._seat_counts.get(seat, 0) + 1