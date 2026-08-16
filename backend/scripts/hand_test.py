"""阶段3 验收脚本：手工摆一个局面，真实调用一次 LLM，打印 prompt + 决策 + 校验。

用法：uv run python backend/scripts/hand_test.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/

from doudizhu import Card  # noqa: E402

from app.key_picker import KeyPicker  # noqa: E402
from app import config  # noqa: E402
from dzcore import dou_dz_adapter as dz  # noqa: E402
from dzcore.ai_llm import LLMAI  # noqa: E402
from dzcore.prompt_builder import build_prompt, remaining_counts  # noqa: E402


def build_view() -> dict:
    hand = Card.card_ints_from_string("3c-5d-5s-9h-9c-10d-Js-Jh-Qd-Ks-Ah-As-2d-2h-BJ")
    bottom = Card.card_ints_from_string("7c-8d-9s")
    # 假设我为 0 号农民，队友 1，地主 2；地主刚出 一对 7，我来压
    last_play = Card.card_ints_from_string("7c-7d")
    history = [
        {"seat": 2, "action": "play", "cards": Card.card_ints_from_string("4c"), "trick": 1},
        {"seat": 0, "action": "play", "cards": Card.card_ints_from_string("3c"), "trick": 1},
        {"seat": 1, "action": "play", "cards": Card.card_ints_from_string("6d"), "trick": 1},
        {"seat": 2, "action": "play", "cards": Card.card_ints_from_string("9s"), "trick": 2},  # noqa: E501
        {"seat": 0, "action": "pass", "cards": [], "trick": 2},
        {"seat": 1, "action": "play", "cards": Card.card_ints_from_string("10h"), "trick": 2},
        {"seat": 2, "action": "play", "cards": Card.card_ints_from_string("Kd"), "trick": 3},
        {"seat": 0, "action": "pass", "cards": [], "trick": 3},
        {"seat": 1, "action": "play", "cards": Card.card_ints_from_string("As"), "trick": 3},
        {"seat": 2, "action": "pass", "cards": [], "trick": 3},
        {"seat": 1, "action": "play", "cards": Card.card_ints_from_string("7c-7d"), "trick": 4},
    ]
    return {
        "me": "你(农民)",
        "seat": 0,
        "role": "farmer",
        "teammate": "队友乙",
        "names": ["你(农民)", "队友乙", "地主丙"],
        "landlord_seat": 2,
        "hand": hand,
        "bottom": bottom,
        "remaining": [15, 14, 16],
        "last_play": last_play,
        "last_play_by": 1,
        "history": history,
        "show_candidates": True,
    }


def main() -> int:
    print(f"=== 使用模型 {config.SENSENOVA_MODEL}，key 数 {len(config.SENSENOVA_API_KEYS)} ===")
    view = build_view()
    print("\n----- PROMPT -----")
    print(build_prompt(view))
    print("\n----- 记牌表预览 -----")
    print(remaining_counts(view["history"]))
    print("\n----- 调用 LLM -----")
    ai = LLMAI(name="手测LLM", picker=KeyPicker(config.SENSENOVA_API_KEYS), show_candidates=True)
    decision = ai.choose_action(view["hand"], view["last_play"], context=view)
    if decision is None:
        print(">>> 决策：过（不出）")
    else:
        print(">>> 决策：出", dz.cards_label(decision), "| 合法:", dz.can_beat(decision, view["last_play"]))
    print(f"\n本轮实际轮询用到的 key 数量级可看日志；_last_key_index={ai._last_key_index}")
    return 0


if __name__ == "__main__":
    sys.exit(main())