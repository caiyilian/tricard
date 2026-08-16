"""斗地主牌型引擎适配层：统一封装 doudizhu 库的卡牌 int 表示与判断。"""

from collections import Counter

from doudizhu import (
    Card,
    cards_greater,
    check_card_type,
    list_greater_cards,
    new_game,
)

# 点数显示顺序（从小到大的库内名称），用于头部与排序
# Card.STR_RANKS: 3,4,5,6,7,8,9,10,J,Q,K,A,2,BJ(小王),CJ(大王)
_RANK_ORDER = {label: i for i, label in enumerate(Card.STR_RANKS)}


def sort_cards(cards: list[int]) -> list[int]:
    """按点数排序（大到小）。"""
    return sorted(cards, key=lambda c: Card.get_rank_int(c), reverse=True)


def card_label(card: int) -> str:
    """单个 int 卡的显示名：3..10,J,Q,K,A,2,BJ,CJ。"""
    return Card.rank_int_to_str(card)


def cards_label(cards: list[int]) -> list[str]:
    """一组卡的显示标签，按点数从大到小排列。"""
    return sorted((card_label(c) for c in cards), key=lambda x: _RANK_ORDER[x], reverse=True)


def deal() -> tuple[list[list[int]], list[int]]:
    """发牌：(三个 17 张手牌, 3 张底牌)。"""
    groups = new_game()
    return groups[:3], groups[3]


def is_valid_play(cards: list[int]) -> bool:
    """是否为合法牌型（单牌/对/三/顺子/飞机/炸弹等）。空列表视为非法。"""
    if not cards:
        return False
    ok, _ = check_card_type(cards)
    return bool(ok)


def play_type(cards: list[int]) -> str | None:
    """返回牌型名称（如 pair / bomb / rocket），非法返回 None。"""
    if not cards:
        return None
    ok, types = check_card_type(cards)
    if not ok:
        return None
    return types[0][0]


def can_beat(new_cards: list[int], last_cards: list[int]) -> bool:
    """new 能否压过 last。last 为空时（领出）只要自身合法即可。"""
    if not last_cards:
        return is_valid_play(new_cards)
    if not is_valid_play(new_cards):
        return False
    greater, _ = cards_greater(new_cards, last_cards)
    return bool(greater)


def has_cards(hand: list[int], cards: list[int]) -> bool:
    """hand 是否包含 cards（论张数，花色无关）。"""
    h = Counter(hand)
    c = Counter(cards)
    return all(h[k] >= v for k, v in c.items())


def list_beating(last_cards: list[int], hand: list[int]) -> list[list[int]]:
    """从 hand 中找出所有能压过 last 的出法。last 为空返回 []（领出请用排列逻辑）。"""
    if not last_cards or not is_valid_play(last_cards):
        return []
    result = []
    groups = list_greater_cards(last_cards, hand)
    for combos in groups.values():
        for combo in combos:
            result.append(combo)
    return result


def minimal_lead(hand: list[int]) -> list[int]:
    """领出时的最小合法出法：打出最小的一张单牌。"""
    if not hand:
        return []
    smallest = min(hand, key=lambda c: Card.get_rank_int(c))
    return [smallest]


def count_bomb_rocket(cards: list[int]) -> bool:
    return play_type(cards) in ("bomb", "rocket")


def labels_to_hand_int(labels: list[str], hand: list[int]) -> list[int] | None:
    """按牌面名称（如 "3","A","BJ"）从手中选出对应 int；数量不足返回 None。"""
    need = Counter(labels)
    remain = Counter(card_label(c) for c in hand)
    if any(remain[l] < n for l, n in need.items()):
        return None
    result: list[int] = []
    used: set[int] = set()
    for l in labels:
        for i, c in enumerate(hand):
            if i in used:
                continue
            if card_label(c) == l:
                result.append(c)
                used.add(i)
                break
    return result