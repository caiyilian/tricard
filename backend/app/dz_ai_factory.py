"""按座位组装出牌 AI（basic/douzero/llm）。"""

from dzcore.ai_basic import BasicAI


def build_ai(ai_type: str, seat) -> object:
    if ai_type == "douzero":
        from dzcore.ai_douzero import DouZeroAI

        return DouZeroAI(name=seat.nickname)
    if ai_type == "llm":
        from app import config
        from app.key_picker import KeyPicker
        from dzcore.ai_llm import LLMAI

        return LLMAI(name=seat.nickname, picker=KeyPicker(config.SENSENOVA_API_KEYS))
    return BasicAI(name=seat.nickname)