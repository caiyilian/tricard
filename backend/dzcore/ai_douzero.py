"""DouZero 强 AI 适配：把 DouZero 深度模型接入本机 AI 接口。

做法：每次决策时，用「当前手牌 - 各座位已出牌 = 起始手牌」重建一套 DouZero GameEnv，
把自己的出牌历史整段回放进去（O(回合数)），让 DouZero 内部状态与我们完全一致，
然后调用它对应座位的 DeepAgent 拿动作，转回本引擎编码并二次校验；失败回退规则 AI。
"""

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
DOUZERO_DIR = Path(__file__).resolve().parents[2] / "third_party" / "DouZero"
if str(DOUZERO_DIR) not in sys.path:
    sys.path.insert(0, str(DOUZERO_DIR))

from app import config  # noqa: E402
from dzcore import dou_dz_adapter as dz  # noqa: E402
from dzcore.ai_basic import BasicAI  # noqa: E402

# 库 int 牌面 -> DouZero 环境点数
_ENV_RANK = {
    "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10,
    "J": 11, "Q": 12, "K": 13, "A": 14, "2": 17, "BJ": 20, "CJ": 30,
}
_ENV_TO_LABEL = {v: k for k, v in _ENV_RANK.items()}


def _to_env(cards: list[int]) -> list[int]:
    """库 int 列表 -> DouZero 动作多集（仅点数，如 [5,5]）。"""
    return [_ENV_RANK[dz.Card.rank_int_to_str(c)] for c in cards]


def seat_to_position(seat: int, landlord_seat: int) -> str:
    if seat == landlord_seat:
        return "landlord"
    if seat == (landlord_seat + 1) % 3:
        return "landlord_down"
    return "landlord_up"


class DouZeroRuntime:
    """缓存三个 DeepAgent（地主 / 下农民 / 上农民），进程内单例。"""

    _cache: dict[str, "DouZeroRuntime"] = {}

    @classmethod
    def get(cls, models_dir: str | None = None) -> "DouZeroRuntime":
        path = models_dir or config.DOUZERO_MODELS_DIR
        key = str(path)
        if key not in cls._cache:
            cls._cache[key] = cls(path)
        return cls._cache[key]

    def __init__(self, models_dir: str):
        import torch  # noqa: F401  (确保 torch 就位)
        from douzero.evaluation.deep_agent import DeepAgent

        md = Path(models_dir)
        self.agents = {
            "landlord": DeepAgent("landlord", str(md / "landlord.ckpt")),
            # landlord_up / landlord_down 都对应农民模型，但权重不同
            "landlord_up": DeepAgent("landlord_up", str(md / "landlord_up.ckpt")),
            "landlord_down": DeepAgent("landlord_down", str(md / "landlord_down.ckpt")),
        }

    def act(self, position: str, infoset) -> list[int]:
        return self.agents[position].act(infoset)


class DouZeroAI:
    def __init__(self, name: str = "DouZero", models_dir: str | None = None, runtime: DouZeroRuntime | None = None):
        self.name = name
        self.models_dir = models_dir or config.DOUZERO_MODELS_DIR
        self._runtime = runtime
        self.fallback = BasicAI(name=f"{name}(兜底)")

    def _get_runtime(self) -> DouZeroRuntime:
        if self._runtime is None:
            self._runtime = DouZeroRuntime.get(self.models_dir)
        return self._runtime

    def choose_action(self, hand: list[int], last_play: list[int], context: dict | None = None) -> list[int] | None:
        game = (context or {}).get("game")
        if game is None:
            return self.fallback.choose_action(hand, last_play)
        try:
            return self._mirror_act(game)
        except Exception:  # noqa: BLE001
            return self.fallback.choose_action(hand, last_play)

    def _mirror_act(self, game) -> list[int] | None:
        from douzero.env.game import GameEnv  # noqa: F401

        class DummyAgent:
            def __init__(self, position):
                self.position = position
                self.action = []

            def act(self, infoset):
                assert self.action in infoset.legal_actions
                return self.action

        # 重建三个起始手牌 = 当前手牌 + 各座位历史出过的牌
        from collections import Counter

        played: list[Counter] = [Counter() for _ in range(3)]
        for e in game.history:
            if e["action"] == "play":
                played[e["seat"]].update(e["cards"])
        initial_hands = [
            game.hands[s] + list(played[s].elements()) for s in range(3)
        ]

        ls = game.landlord_seat
        players = {p: DummyAgent(p) for p in ("landlord", "landlord_down", "landlord_up")}
        env = GameEnv(players)
        env.card_play_init(
            {
                "landlord": _to_env(initial_hands[ls]),
                "landlord_down": _to_env(initial_hands[(ls + 1) % 3]),
                "landlord_up": _to_env(initial_hands[(ls - 1) % 3]),
                "three_landlord_cards": _to_env(game.bottom),
            }
        )

        # 回放历史
        seq = list(game.history)
        for e in seq:
            pos = seat_to_position(e["seat"], ls)
            players[pos].action = [] if e["action"] == "pass" else _to_env(e["cards"])
            env.step()

        # 轮到我：取对应位置模型决策
        my_pos = seat_to_position(game.turn, ls)
        raw = self._get_runtime().act(my_pos, env.game_infoset)
        if not isinstance(raw, list):
            raw = list(raw)

        # 转回本引擎 int：从我的手牌挑对应点数
        chosen = _env_action_to_lib(raw, game.hands[game.turn])
        if chosen is None:
            return self.fallback.choose_action(game.hands[game.turn], game.last_play)
        if not dz.can_beat(chosen, game.last_play):
            return self.fallback.choose_action(game.hands[game.turn], game.last_play)
        return chosen


def _env_action_to_lib(action: list[int], hand: list[int]) -> list[int] | None:
    """DouZero 动作（点数多集）→ 从手牌 int 中挑出对应牌面；张数不足返回 None。"""
    labels = _ENV_TO_LABEL.get
    return dz.labels_to_hand_int([labels(v) for v in action], hand) if action else None