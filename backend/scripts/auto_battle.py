"""规则 AI 验收脚本：三个 AI 自动对战 N 盘，统计胜负与异常。

用法：uv run python backend/scripts/auto_battle.py [N] [--seed base] [--mix basic,basic,basic]
"""

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/

from dzcore.ai_basic import BasicAI  # noqa: E402
from dzcore.game import Game  # noqa: E402


def _make_basic(name, _kind):
    return BasicAI(name=name)


def _make_llm(name, _kind):
    from dzcore.ai_llm import LLMAI
    from app.key_picker import KeyPicker
    from app import config

    return LLMAI(name=name, picker=KeyPicker(config.SENSENOVA_API_KEYS))


def _make_douzero(name, _kind):
    from dzcore.ai_douzero import DouZeroAI

    return DouZeroAI(name=name)


AI_FACTORIES = {
    "basic": _make_basic,
    "llm": _make_llm,
    "douzero": _make_douzero,
}

# 上下文：AI 出牌时把当前 game 对象传进去，供 DouZero 重放使用
_current_game: dict = {}


def _ctx():
    return {"game": _current_game.get("game")}


def build_players(mix: list[str]) -> list:
    factories = []
    for kind in mix:
        if kind not in AI_FACTORIES:
            raise SystemExit(f"unknown AI kind: {kind} (available: {list(AI_FACTORIES)})")
        factories.append(kind)
    return [AI_FACTORIES[kind](f"AI-{i + 1}", kind) for i, kind in enumerate(factories)]


def play_one(players: list, seed: int) -> dict:
    game = Game()
    game.start_quick(seed=seed)
    _current_game["game"] = game
    turns = 0
    while game.status == Game.STATUS_PLAYING:
        turns += 1
        assert turns < 1000, f"possible infinite loop at seed {seed}"
        seat = game.turn
        move = players[seat].choose_action(game.hands[seat], game.last_play, _ctx())
        if move is None:
            assert game.do_pass(seat)
        else:
            assert game.can_play(seat, move), f"illegal move by seat {seat}: {move}"
            assert game.play(seat, move)
    return {"turns": turns, "winner": game.winner_team, "seat": game.winner_seat, "bombs": game.bomb_count}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("games", type=int, nargs="?", default=100)
    parser.add_argument("--seed", type=int, default=0, help="随机基值，0 表示随机")
    parser.add_argument("--mix", default="basic,basic,basic", help="逗号分隔的座位 AI 类型")
    args = parser.parse_args()

    mix = [k.strip() for k in args.mix.split(",")]
    if len(mix) != 3:
        raise SystemExit("--mix 需要恰好 3 个座位")

    players = build_players(mix)
    wins = {"landlord": 0, "farmers": 0}
    total_turns = 0
    crashed = 0
    for i in range(args.games):
        seed = (args.seed + i) if args.seed else random.randrange(1 << 30)
        try:
            r = play_one(players, seed)
            wins[r["winner"]] += 1
            total_turns += r["turns"]
        except Exception as e:  # noqa: BLE001
            crashed += 1
            print(f"[{i}] CRASH seed={seed}: {type(e).__name__}: {e}")

    avg = total_turns / max(args.games - crashed, 1)
    print(f"mix={args.mix} games={args.games} crashed={crashed}")
    print(f"landlord wins={wins['landlord']} | farmers wins={wins['farmers']} | avg turns={avg:.1f}")
    return 1 if crashed else 0


if __name__ == "__main__":
    sys.exit(main())