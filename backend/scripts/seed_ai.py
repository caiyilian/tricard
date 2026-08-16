"""建表 + 创建 AI 账号 + 回补欢乐豆（幂等）。

用法：
    uv run python backend/scripts/seed_ai.py --ensure      # 建表并确保 AI 账号存在
    uv run python backend/scripts/seed_ai.py --refill      # 把 AI 欢乐豆回补到初始值
    uv run python backend/scripts/seed_ai.py --ensure --initial 50000 --count 8
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/

from sqlalchemy.orm import Session  # noqa: E402

from app import security  # noqa: E402
from app.db import SessionLocal, init_db  # noqa: E402
from app.models import User  # noqa: E402

DEFAULT_AI = [
    ("ai_laozhao", "地主老赵"),
    ("ai_xiaomei", "豆子小美"),
    ("ai_damowang", "牌场大魔王"),
    ("ai_wangjie", "王姐"),
    ("ai_tiezhu", "老铁"),
    ("ai_lihua", "李花"),
    ("ai_yeye", "牌仙爷爷"),
    ("ai_dabing", "大兵"),
]


def ensure_ai(db: Session, names: list[tuple[str, str]], initial_beans: int) -> list[User]:
    created = 0
    for username, nickname in names:
        if db.query(User).filter(User.username == username).first():
            continue
        db.add(
            User(
                username=username,
                password_hash=security.hash_password("ai-bot-no-login"),
                nickname=nickname,
                is_ai=True,
                joy_beans=initial_beans,
            )
        )
        created += 1
    db.commit()
    return created


def refill_ai(db: Session, initial_beans: int) -> int:
    bots = db.query(User).filter(User.is_ai.is_(True)).all()
    for b in bots:
        b.joy_beans = initial_beans
    db.commit()
    return len(bots)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ensure", action="store_true", help="建表并确保 AI 账号存在")
    parser.add_argument("--refill", action="store_true", help="把 AI 欢乐豆回补到初始值")
    parser.add_argument("--initial", type=int, default=100000, help="AI 初始欢乐豆")
    parser.add_argument("--count", type=int, default=None, help="只创建前 N 个 AI 账号")
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    names = DEFAULT_AI if args.count is None else DEFAULT_AI[: args.count]

    if args.ensure:
        created = ensure_ai(db, names, args.initial)
        print(f"AI accounts ensured: {len(names)} (new={created}, initial beans={args.initial})")
    if args.refill:
        n = refill_ai(db, args.initial)
        print(f"AI beans refilled: {n} accounts -> {args.initial}")
    if not args.ensure and not args.refill:
        parser.print_help()

    bots = db.query(User).filter(User.is_ai.is_(True)).all()
    print(f"current AI accounts: {len(bots)}")
    for b in bots:
        print(f"  {b.nickname:8s} @{b.username}  beans={b.joy_beans}  wins={b.wins} losses={b.losses}")
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())