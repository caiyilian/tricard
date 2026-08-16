"""评论编排器：订阅对局事件 → 探测 → 频控 →（规则短语 | LLM 评论）→ emit 广播。

调用方（房间层）在「天然停顿处」调用 maybe_comment(game)：整轮结束、炸弹出现、终局。
"""

import random

from app import config
from dzcore.commentary import detector, phrase_bank
from dzcore.commentary.llm_commentator import LLMCommentator
from dzcore.commentary.salience import FrequencyController

_MODE = config.COMMENTATOR_MODE  # rules_only / hybrid / llm_judge


class Commentator:
    def __init__(
        self,
        seats: list[dict],
        mode: str = _MODE,
        picker=None,
        emit=None,
        llm=None,
    ):
        """seats: [{"seat":int,"name":str,"personality":"savage"}...]（只含 AI 座位）"""
        self.seats = [s for s in seats if s.get("ai", True)]
        self.mode = mode
        self.emit = emit or (lambda c: None)
        self.freq = FrequencyController()
        self.llm: LLMCommentator | None = llm
        if picker is not None:
            self.llm = self.llm or LLMCommentator(picker=picker)

    def maybe_comment(self, game, reason: str = ""):
        if not self.seats:
            return
        events = detector.detect(game)
        if not events:
            return
        # 显著度累计（按目标座位）
        for ev in events[:1]:  # 每轮最多处理一个最显著事件（防刷屏）
            target = self._pick_speaker_for(ev)
            if target is None:
                continue
            self.freq.add_salience(ev["target_seat"], ev["intensity"])
            sal = self.freq.consume(ev["target_seat"])
            if sal < 2:
                continue
            turn = len(game.history)
            trick = game.history[-1]["trick"] if game.history else 1
            if not self.freq.can_comment(target["seat"], turn, trick):
                continue
            self.freq.mark_comment(target["seat"], turn)
            comment = self._produce(ev, target, game)
            if comment:
                self.emit(comment)

    def _pick_speaker_for(self, ev: dict) -> dict | None:
        """选发言人：优先选非目标的 AI 座位。"""
        candidates = [s for s in self.seats if s["seat"] != ev["target_seat"]]
        if not candidates:
            candidates = self.seats
        return random.choice(candidates)

    def _produce(self, ev: dict, speaker: dict, game) -> dict | None:
        target = next(
            (s["name"] for s in self.seats if s["seat"] == ev["target_seat"]),
            f"座位{ev['target_seat']}",
        )
        snap = self._snapshot(ev, target)

        if self.mode in ("hybrid", "llm_judge") and self.llm is not None:
            dec = self.llm.decide(snap)
            if dec:
                return {
                    "type": "comment",
                    "seat": speaker["seat"],
                    "speaker": speaker["name"],
                    "personality": speaker.get("personality", "savage"),
                    "text": dec["text"],
                    "archetype": ev["archetype"],
                }
        text = phrase_bank.pick(
            ev["archetype"],
            target=target,
            self_name=speaker["name"],
            mate=self._mate_name(speaker["seat"], game),
            personality=speaker.get("personality", "savage"),
        )
        return {
            "type": "comment",
            "seat": speaker["seat"],
            "speaker": speaker["name"],
            "personality": speaker.get("personality", "savage"),
            "text": text,
            "archetype": ev["archetype"],
        }

    def _snapshot(self, ev: dict, target: str) -> dict:
        return {
            "event_desc": f"{target} 触发了「{ev['archetype']}」动作，强度 {ev['intensity']}",
            "names": [s["name"] for s in self.seats],
        }

    def _mate_name(self, seat: int, game) -> str:
        try:
            ls = game.landlord_seat
            if seat != ls:
                mate = [s for s in range(3) if s != ls and s != seat]
                if mate:
                    return f"座位{mate[0]}"
        except Exception:  # noqa: BLE001
            pass
        return "队友"