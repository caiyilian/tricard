"""局面探测器：对局历史/状态 -> 确定性"坑/亮点"事件（非随机）。

输入 game（dzcore.Game），输出候选事件列表：
    {archetype, target_seat, intensity}
只识别可被确定断言的关键局面；其余交给游戏结果兜底话术。
"""

from collections import Counter

ROLE_LANDLORD = "landlord"
ROLE_FARMER = "farmers"


def _is_bomb(labels: list[str]) -> bool:
    if sorted(labels) == ["BJ", "CJ"]:
        return True
    return len(labels) == 4 and len(set(labels)) == 1


def trick_winner(history: list[dict], trick: int) -> int | None:
    """该轮最后一个出牌的人（即本轮胜者）。"""
    winner = None
    for e in history:
        if e["trick"] != trick:
            continue
        if e["action"] == "play":
            winner = e["seat"]
    return winner


def detect(game, trick_events: list[dict] | None = None) -> list[dict]:
    """返回候选事件列表。trick_events 用于按轮分析（由 caller 提供分组）。"""
    events: list[dict] = []
    hist = game.history
    if not hist:
        return events
    landlord = game.landlord_seat
    farmer_seats = [s for s in range(3) if s != landlord]

    def is_farmer(seat):
        return seat != landlord

    # ---- 逐轮分析 ----
    # 对历史按 trick 分组
    tricks: dict[int, list[dict]] = {}
    for e in hist:
        tricks.setdefault(e["trick"], []).append(e)
    trick_ids = sorted(tricks)

    for tid in trick_ids:
        moves = tricks[tid]
        winner = trick_winner(hist, tid)

        # 踩队友：同一轮里，某农民压过其农民队友，随后被地主压过且地主赢得此轮
        for i, m in enumerate(moves):
            if m["action"] != "play" or not is_farmer(m["seat"]):
                continue
            # 找这一轮中更早的"农民出牌"
            for j in range(i):
                prev = moves[j]
                if prev["action"] == "play" and is_farmer(prev["seat"]) and prev["seat"] != m["seat"]:
                    if winner == landlord:
                        events.append({"archetype": "keng_step", "target_seat": m["seat"], "intensity": 2})
                        break

        # 不送牌：这轮里有农民领出，且其队友剩 1 张，却出了非单张
        for m in moves:
            if m["action"] != "play" or len(m["cards"]) == 0:
                continue
            # 领出判定：这轮第一个出牌动作
            first_play = next((x for x in moves if x["action"] == "play"), None)
            if first_play is None or first_play["seat"] != m["seat"]:
                continue
            if len(m["cards"]) > 1 and is_farmer(m["seat"]):
                mate = [s for s in farmer_seats if s != m["seat"]]
                for s in mate:
                    # 用剩余张数（history 里该动作后的 hand_left）判断队友剩牌
                    after = _hand_left_after(moves, s, m["hand_left"])
                    if after == 1:
                        events.append({"archetype": "keng_no_send", "target_seat": m["seat"], "intensity": 2})
                        break

        # 自己人互炸：相邻两个炸弹分别来自两个农民
        bombers = []
        for m in moves:
            if m["action"] == "play" and m["labels"] and _is_bomb(m["labels"]):
                bombers.append(m["seat"])
        for i in range(len(bombers) - 1):
            a, b = bombers[i], bombers[i + 1]
            if (
                a != b
                and is_farmer(a)
                and is_farmer(b)
            ):
                events.append({"archetype": "keng_friendly_fire", "target_seat": a, "intensity": 3})
                break

        # 帮倒忙（简化：地主赢得此轮且农民有人"喂"了大牌给地主）
        if winner == landlord:
            for m in moves:
                if m["action"] == "play" and is_farmer(m["seat"]) and len(m["cards"]) >= 5:
                    events.append({"archetype": "keng_boost", "target_seat": m["seat"], "intensity": 2})
                    break

    # ---- 整局分析 ----
    if game.status == game.STATUS_FINISHED:
        # 神炸/送跑/绝地/送葬
        # 神炸：本方使用炸弹且获胜
        bomb_scores: dict[int, int] = Counter()
        for e in hist:
            if e["action"] == "play" and e["labels"] and _is_bomb(e["labels"]):
                bomb_scores[e["seat"]] += 1
        winner_team = game.winner_team
        for seat, n in bomb_scores.items():
            if game.team_of(seat) == winner_team and n > 0:
                events.append({"archetype": "bright_bomb", "target_seat": seat, "intensity": 2})

        # 送跑：农民队友剩1，农民送出单张，队友出完获胜
        if winner_team == ROLE_FARMER:
            winner = game.winner_seat
            # 查胜负手：最后一个出牌动作
            last = hist[-1] if hist else None
            if last and last["seat"] == winner and len(last["cards"]) == 1:
                # 前一轮有队友领出单张
                prev_plays = [e for e in hist[:-1] if e["action"] == "play" and is_farmer(e["seat"]) and e["seat"] != winner and len(e["cards"]) == 1]
                if prev_plays:
                    events.append({"archetype": "bright_send", "target_seat": prev_plays[-1]["seat"], "intensity": 2})

        # 送葬/绝地：按中途手牌优劣势做判断（简化：谁手牌总量前期领先）
        if winner_team == ROLE_LANDLORD:
            events.append({"archetype": "keng_blow", "target_seat": farmer_seats[0], "intensity": 1})
        else:
            events.append({"archetype": "bright_comeback", "target_seat": game.winner_seat, "intensity": 1})

    return events


def _hand_left_after(moves: list[dict], seat: int, fallback: int) -> int:
    """某座位在该轮结束后的手牌数（从最后一个动作取）。"""
    for m in reversed(moves):
        if m["seat"] == seat:
            return m["hand_left"]
    return fallback