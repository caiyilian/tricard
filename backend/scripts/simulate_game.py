"""阶段1 验收脚本：用简单贪心策略打完一局，逐步打印，每步都必须合法。

用法：uv run python backend/scripts/simulate_game.py [seed] [--max-turns N]
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/

from dzcore import dou_dz_adapter as dz  # noqa: E402
from dzcore.game import Game  # noqa: E402


def label(seat: int, game: Game) -> str:
    return ("地主" if seat == game.landlord_seat else "农民") + f"[{seat}]"


def choose_move(game: Game, seat: int) -> list[int] | None:
    if game.can_pass(seat):
        combos = dz.list_beating(game.last_play, game.hands[seat])
        if combos:
            combos.sort(key=lambda c: (len(c), -min(dz.Card.get_rank_int(x) for x in c)))
            return combos[0]
        return None
    return dz.minimal_lead(game.hands[seat])


def simulate(seed: int | None, max_turns: int = 1000) -> Game:
    game = Game()
    game.start_quick(seed=seed)
    print(f"=== 新一局 seed={seed} 地主={game.landlord_seat} 底牌={dz.cards_label(game.bottom)} ===")
    for seat in range(3):
        print(f"{label(seat, game)} 手牌: {dz.cards_label(game.hands[seat])}")

    turns = 0
    while game.status == Game.STATUS_PLAYING:
        turns += 1
        assert turns <= max_turns, "turn limit exceeded"
        seat = game.turn
        move = choose_move(game, seat)
        if move is None:
            assert game.can_pass(seat)
            game.do_pass(seat)
            print(f"  T{turns}{label(seat, game)}: 过")
        else:
            assert game.can_play(seat, move), f"illegal play by seat {seat}: {move}"
            game.play(seat, move)
            kind = dz.play_type(move)
            extra = " 💣" if kind in ("bomb", "rocket") else ""
            print(f"  T{turns} {label(seat, game)}: {dz.cards_label(move)} ({kind}){extra}")

    print(f"=== 终局 胜方={game.winner_team} 胜利座位={game.winner_seat} 炸弹数={game.bomb_count} 回合数={turns} ===")
    return game


if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else random.randrange(100000)
    max_turns = 1000
    if "--max-turns" in sys.argv:
        max_turns = int(sys.argv[sys.argv.index("--max-turns") + 1])
    simulate(seed, max_turns=max_turns)