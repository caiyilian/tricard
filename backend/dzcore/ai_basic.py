"""规则 AI（兜底，贪心策略）。

统一接口：
    BasicAI.choose_action(hand, last_play) -> list[int] | None
       返回要出的牌 int 列表；None 表示「过」。
"""

from collections import Counter

from doudizhu import Card

from . import dou_dz_adapter as dz


def _rank(card: int) -> int:
    return Card.get_rank_int(card)


def _cost(combos: list[list[int]]) -> list[list[int]]:
    """按「先张数少、再点数小」排序出牌候选。"""
    return sorted(combos, key=lambda c: (len(c), _rank(c[0])))


def _lead_play(hand: list[int]) -> list[int]:
    """领出拆牌：优先丢最小的散单；无散单则最小对子；再是三张；兜底最小单。"""
    counts = Counter(_rank(c) for c in hand)
    singles = [c for c in hand if counts[_rank(c)] == 1]
    if singles:
        return [min(singles, key=_rank)]
    pairs = {r for r, n in counts.items() if n == 2}
    if pairs:
        r = min(pairs)
        pair = [c for c in hand if _rank(c) == r][:2]
        return pair
    trios = {r for r, n in counts.items() if n >= 3}
    if trios:
        r = min(trios)
        trio = [c for c in hand if _rank(c) == r][:3]
        return trio
    return dz.minimal_lead(hand)


class BasicAI:
    def __init__(self, name: str = "规则AI"):
        self.name = name

    def choose_action(self, hand: list[int], last_play: list[int], context: dict | None = None) -> list[int] | None:
        if last_play:
            combos = dz.list_beating(last_play, hand)
            if not combos:
                return None
            return _cost(combos)[0]
        return _lead_play(hand)