"""排行榜查询：三榜（欢乐豆 / 胜场 / 胜率）、Top N、可选过滤 AI。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .db import get_db
from .models import User

router = APIRouter(prefix="/api/ranking", tags=["ranking"])

SORT_BY = {"beans": User.joy_beans, "wins": User.wins}
MIN_GAMES_FOR_WIN_RATE = 5
DEFAULT_LIMIT = 50
MAX_LIMIT = 200


@router.get("")
def get_ranking(
    by: str = "beans",
    limit: int = DEFAULT_LIMIT,
    include_ai: bool = True,
    db: Session = Depends(get_db),
):
    if by not in SORT_BY and by != "win_rate":
        return {"error": f"by 必须是 beans/wins/win_rate 之一", "items": []}
    limit = max(1, min(limit, MAX_LIMIT))

    q = db.query(User)
    if not include_ai:
        q = q.filter(User.is_ai.is_(False))

    if by == "win_rate":
        items = [u for u in q.all() if u.games >= MIN_GAMES_FOR_WIN_RATE]
        items.sort(key=lambda u: (u.win_rate or 0, u.games), reverse=True)
    else:
        items = q.order_by(SORT_BY[by].desc()).all()

    return {"by": by, "items": [u.public() for u in items[:limit]]}