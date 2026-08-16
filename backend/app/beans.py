"""欢乐豆结算（纯函数）：返回每个角色的豆子增减与翻倍系数。服务端权威。

乘法规则（市面同款）：
    multiplier = 2^炸弹数(含王炸) × (2 if 春天 else 1)
    地主胜：地主 +2×base×mult；两农民各 -base×mult
    地主负：地主 -2×base×mult；两农民各 +base×mult
欢乐豆可为负。
"""


def multiplier(bombs: int, spring: bool) -> int:
    return (2 ** bombs) * (2 if spring else 1)


def settle(base_bet: int, bombs: int, spring: bool, landlord_win: bool) -> dict[str, int]:
    mult = multiplier(bombs, spring)
    farmer_delta = (-base_bet * mult) if landlord_win else (base_bet * mult)
    landlord_delta = 2 * (-farmer_delta)  # 地主赢 = 两份农民负；地主输 = 两份农民正
    return {"landlord": landlord_delta, "farmer": farmer_delta, "multiplier": mult}


def settle_by_players(
    usernames: list[str], landlord_index: int, base_bet: int, bombs: int, spring: bool, landlord_win: bool
) -> dict[str, int]:
    """按用户名结算三席位。usernames 长度 3（[0..2]），landlord_index 指向地主。"""
    d = settle(base_bet, bombs, spring, landlord_win)
    result: dict[str, int] = {}
    for i, name in enumerate(usernames):
        role = "landlord" if i == landlord_index else "farmer"
        result[name] = d[role]
    return result