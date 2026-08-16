"""按房间座位组装评论器并接上线。"""

from app import config
from app.key_picker import KeyPicker


def make_commentator(room, sio):
    """返回 Commentator；AI 座位人格 off 则跳过该座位。"""
    from dzcore.commentary.commentator import Commentator

    ai_seats = [
        {
            "seat": i,
            "name": s.nickname,
            "personality": s.personality,
            "ai": True,
        }
        for i, s in enumerate(room.seats)
        if s and s.is_ai and s.personality != "off"
    ]
    if not ai_seats:
        return None
    return Commentator(
        seats=ai_seats,
        mode=config.COMMENTATOR_MODE,
        picker=KeyPicker(config.SENSENOVA_API_KEYS),
        emit=lambda c: sio.start_background_task(_emit_comment, sio, room.code, c),
    )


async def _emit_comment(sio, code: str, comment: dict) -> None:
    await sio.emit("comment", comment, to=f"room:{code}")


# 兼容旧引用：无实时 socket 时用显式 emit
def make_commentator_emit(room, emit):
    from dzcore.commentary.commentator import Commentator

    ai_seats = [
        {
            "seat": i,
            "name": s.nickname,
            "personality": s.personality,
            "ai": True,
        }
        for i, s in enumerate(room.seats)
        if s and s.is_ai and s.personality != "off"
    ]
    if not ai_seats:
        return None
    return Commentator(seats=ai_seats, mode=config.COMMENTATOR_MODE, picker=KeyPicker(config.SENSENOVA_API_KEYS), emit=emit)