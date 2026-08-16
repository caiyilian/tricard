"""阶段 4.5 验收脚本：多局模拟中统计评论数量，验证不刷屏。

用法：uv run python backend/scripts/comment_sim.py 50 [--mode rules_only]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/

from dzcore.ai_basic import BasicAI  # noqa: E402
from dzcore.commentary.commentator import Commentator  # noqa: E402
from dzcore.game import Game  # noqa: E402

AI_SEAT_TEMPLATE = [
    {"seat": 0, "name": "地主老赵", "personality": "savage", "ai": True},
    {"seat": 1, "name": "豆子小美", "personality": "kind", "ai": True},
    {"seat": 2, "name": "牌场大魔王", "personality": "savage", "ai": True},
]


def run_one(seed: int, mode: str) -> dict:
    comments: list[dict] = []
    game = Game()
    game.start_quick(seed=seed)
    players = [BasicAI(name="p0"), BasicAI(name="p1"), BasicAI(name="p2")]
    com = Commentator(seats=AI_SEAT_TEMPLATE, mode=mode, emit=comments.append)
    prev_trick = 0
    while game.status == Game.STATUS_PLAYING:
        seat = game.turn
        move = players[seat].choose_action(game.hands[seat], game.last_play)
        if move is None:
            game.do_pass(seat)
        else:
            game.play(seat, move)
        # 整轮结束（进入新 trick）时给评论一个天然停顿点
        if game.history and game.history[-1]["trick"] != prev_trick:
            prev_trick = game.history[-1]["trick"]
            com.maybe_comment(game)
    com.maybe_comment(game)  # 终局

    seat_counts = {}
    for c in comments:
        seat_counts[c["seat"]] = seat_counts.get(c["seat"], 0) + 1
    return {"total": len(comments), "seat_counts": seat_counts}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("games", type=int, nargs="?", default=50)
    parser.add_argument("--mode", default="rules_only", choices=["rules_only", "hybrid", "llm_judge"])
    args = parser.parse_args()

    total_comments = 0
    over_cap = 0
    for seed in range(1, args.games + 1):
        r = run_one(seed, args.mode)
        # 每桌每局最多 ~ per_trick_max*轮次 + 终局，兜底断言全局不爆炸
        if r["total"] > 12:
            over_cap += 1
        total_comments += r["total"]
        print(f"seed={seed:3d} comments={r['total']:2d}")

    avg = total_comments / args.games
    print(f"mode={args.mode} games={args.games} avg_comments={avg:.1f} games_over_12={over_cap}")
    return 1 if over_cap > args.games * 0.1 else 0


if __name__ == "__main__":
    sys.exit(main())