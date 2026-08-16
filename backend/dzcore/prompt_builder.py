"""LLM 局面快照（"开卷考"）构建器：把局面转成可读的中文 prompt。

view 结构约定（由上层 Game/Room 组装，或手测脚本手写）：
{
  "me": "张三",            # 我的名字
  "seat": 0,              # 我的座位 0..2
  "role": "landlord|farmer",
  "teammate": "李四",      # 农民时队友名，地主时 None
  "hand": [int],          # 我的手牌（库 int 编码）
  "bottom": [int],        # 底牌（仅地主可见，显式传给双方都能知道，正式规则农民不可见——由上层决定传不传）
  "remaining": [17, 17, 20],  # 每位剩牌数 [seat0, seat1, seat2]
  "names": ["张三","李四","王五"],  # 座位名字
  "landlord_seat": 2,
  "last_play": [int] | None,   # 上一手（需压过）；None 表示领出
  "last_play_by": 2 | None,
  "history": [ {"seat":0,"action":"play|pass","cards":[int], "trick":1}, ... ],
  "show_candidates": bool,     # 是否附合法可压牌型列表（LLM_HINT_CANDIDATES）
}
"""

from doudizhu import Card

from app import config
from dzcore import dou_dz_adapter as dz

_CARD_STR = ["3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A", "2", "BJ", "CJ"]
# 全副牌点数张数：3~2 各 4 张 + 小王 + 大王
DECK_COUNTS = {r: 4 for r in _CARD_STR[:-2]}
DECK_COUNTS.update({"BJ": 1, "CJ": 1})


def _rl(cards: list[int]) -> list[str]:
    return dz.cards_label(cards)


def remaining_counts(history: list[dict]) -> dict[str, int]:
    """记牌表：从历史出牌反推「每点剩余未知总数」（含底牌与所有未亮牌）。"""
    played = {r: 0 for r in DECK_COUNTS}
    for e in history:
        if e["action"] == "play":
            for c in e["cards"]:
                played[Card.rank_int_to_str(c)] += 1
    return {r: DECK_COUNTS[r] - played[r] for r in DECK_COUNTS}


def build_prompt(view: dict) -> str:
    me = view["me"]
    role = view["role"]
    names = view["names"]
    hand = view["hand"]
    remaining = view["remaining"]

    lines: list[str] = []
    lines.append("你是一名斗地主玩家，现在轮到你出牌。请结合局势做出合理决策。")

    # 身份
    if role == "landlord":
        lines.append(f"【身份】你是 {me}，身份【地主】。你的目标是：你优先出完手牌，赢过两位农民。")
    else:
        mate = view.get("teammate") or "（队友）"
        lines.append(f"【身份】你是 {me}，身份【农民】。你的队友是 {mate}。目标是：你或你的队友任一人先出完即胜利。")

    # 手牌
    lines.append("【我的手牌】" + " ".join(_rl(hand)) + f"（共 {len(hand)} 张）")

    # 剩余
    parts = " | ".join(
        f"{names[i]}:{remaining[i]}张" + ("（你）" if i == view["seat"] else "（地主）" if i == view["landlord_seat"] else "")
        for i in range(3)
    )
    lines.append("【剩余牌数】" + parts)

    # 当前
    lp = view.get("last_play")
    if lp:
        who = names[view["last_play_by"]] if view.get("last_play_by") is not None else "上家"
        lines.append(f"【当前】该你出牌，上一手是 {who} 出的：{' '.join(_rl(lp))}。你可以压过它，也可以出炸弹/王炸，或选择不出（过）。")
    else:
        lines.append("【当前】该你领出（你是本轮第一个出牌的人），必须出牌，不能过。")

    # 历史
    hist = view.get("history") or []
    if hist:
        lines.append("【出牌记录】（trick.座位 动作 牌）")
        for e in hist:
            who = names[e["seat"]]
            if e["action"] == "pass":
                lines.append(f"  第{e['trick']}轮 {who}:过")
            else:
                lines.append(f"  第{e['trick']}轮 {who}:{' '.join(_rl(e['cards']))}")

    # 记牌表
    counts = remaining_counts(hist)
    table = "  ".join(f"{k}剩{v}" for k, v in counts.items() if v < DECK_COUNTS[k])
    lines.append("【记牌表】（已出牌后每点剩余总数）")
    lines.append("  " + (table if table else "开局尚无出牌"))

    # 候选提示（可选）
    if view.get("show_candidates") and lp:
        cands = dz.list_beating(lp, hand)
        if cands:
            shown = [" ".join(_rl(c)) for c in cands[:6]]
            lines.append("【合法可压提示】你可以从以下组合中选（也可另选合法组合）：")
            lines.append("  " + " | ".join(shown))

    # 规则与输出约束
    lines.append(
        "【规则】牌型：单张/对子/三张/三带一/三带二/顺子(≥5张)/连对(≥3对)/飞机/炸弹/王炸。"
        "必须只能出你手中的牌；要压过就必须同类型且更大，或用炸弹/王炸；无法压过则选择'过'。"
        "如果上一手为空（领出），不能'过'。"
    )
    lines.append(
        '【输出】只输出一个 JSON 对象，不要任何其他文字、解释或标记：'
        '  {"action": "play", "cards": ["3", "A"]}   表示出牌'
        '  或 {"action": "pass"}                       表示不出'
    )
    lines.append('注意：cards 里的牌必须是你手牌中真实存在的牌面。')
    return "\n".join(lines)