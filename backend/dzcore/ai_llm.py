"""LLM 决策层：构建 prompt → 调 SenseNova（JSON 模式、关思考）→ 二次校验 → 回退规则 AI。

失败也绝不阻塞：非法 JSON / 非法出牌 → 重试 1 次 → 规则 AI 兜底。
"""

import json
import logging

from openai import OpenAI

from app import config
from app.key_picker import KeyPicker
from dzcore import dou_dz_adapter as dz
from dzcore.ai_basic import BasicAI
from dzcore.prompt_builder import build_prompt

logger = logging.getLogger("tricard.llm_ai")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("openai._base_client").setLevel(logging.WARNING)

INVALID = object()  # 解析出来但不符合规则的决策


class LLMAI:
    def __init__(
        self,
        name: str,
        picker: KeyPicker | None = None,
        model: str | None = None,
        base_url: str | None = None,
        max_tokens: int = 160,
        show_candidates: bool = True,
    ):
        self.name = name
        self.picker = picker or KeyPicker(config.SENSENOVA_API_KEYS)
        self.model = model or config.SENSENOVA_MODEL
        self.base_url = base_url or config.SENSENOVA_BASE_URL
        self.max_tokens = max_tokens
        self.show_candidates = show_candidates
        self.fallback = BasicAI(name=f"{name}(规则兜底)")
        self._last_key_index: int | None = None

    # -- 便于测试替换的传输层 --
    def _chat(self, api_key: str, prompt: str, timeout: float = config.SENSENOVA_TIMEOUT) -> str:
        client = OpenAI(api_key=api_key, base_url=self.base_url, timeout=timeout)
        resp = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=self.max_tokens,
            reasoning_effort="none",
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content
        if not content:
            raise ValueError("empty content from LLM")
        return content

    # -- 主决策入口 --
    def choose_action(self, hand: list[int], last_play: list[int], context: dict | None = None) -> list[int] | None:
        """返回要出的牌 int 列表；None 表示「过」。"""
        view = dict(context or {})
        view.setdefault("hand", hand)
        view.setdefault("last_play", last_play or None)
        view.setdefault("show_candidates", self.show_candidates)
        view["me"] = view.get("me") or self.name
        view.setdefault("role", "farmer")
        if "names" not in view:
            view["names"] = [view["me"], "上家", "下家"]
            view["seat"] = 0
            view["landlord_seat"] = 1
            view["remaining"] = view.get("remaining") or [len(hand) + 10, len(hand) + 10, len(hand) + 10]
        if "teammate" not in view:
            view["teammate"] = view["names"][(view.get("seat", 0) + 1) % 3] if view["role"] == "farmer" else None

        prompt = build_prompt(view)

        for attempt in range(2):
            idx, key = self.picker.next()
            self._last_key_index = idx
            try:
                text = self._chat(key, prompt)
                parsed = json.loads(text)
            except Exception as e:  # noqa: BLE001
                logger.warning("LLM call error (attempt %d): %s", attempt + 1, e)
                self.picker.report_failure(idx)
                continue

            self.picker.report_success(idx)
            decision = self._validate(parsed, hand, last_play)
            if decision is not INVALID:
                return decision

        logger.warning("LLM produced no valid decision after 2 tries; fallback to rule AI")
        return self.fallback.choose_action(hand, last_play)

    def _validate(self, parsed: dict, hand: list[int], last_play: list[int]):
        """返回：list[int]=出的牌 / None=合法'过' / INVALID=非法决策。"""
        action = str(parsed.get("action", "")).lower()
        if action == "pass":
            # 只有上家出过牌（有可以压的上一手）时「过」才合法；领出不能过
            if not last_play:
                return INVALID
            return None
        raw_cards = parsed.get("cards")
        if not isinstance(raw_cards, list) or not raw_cards:
            return INVALID
        raw_labels = [str(c) for c in raw_cards]
        chosen = dz.labels_to_hand_int(raw_labels, hand)
        if chosen is None:
            return INVALID
        if not dz.can_beat(chosen, last_play):
            return INVALID
        return chosen