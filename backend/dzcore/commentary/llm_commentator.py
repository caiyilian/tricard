"""评论 LLM（每桌一个）：判断是否值得说 + 指定发言人 + 生成措辞。

输出要求 JSON：{"should_comment": bool, "speaker": "座位名或'地主'/'农民X'", "text": "…"}
失败/超时由调用方回退短语库。
"""

import json
import logging

from openai import OpenAI

from app import config
from app.key_picker import KeyPicker

logger = logging.getLogger("tricard.commentator")


class LLMCommentator:
    def __init__(self, picker: KeyPicker | None = None, model: str | None = None, base_url: str | None = None):
        self.picker = picker or KeyPicker(config.SENSENOVA_API_KEYS)
        self.model = model or config.SENSENOVA_MODEL
        self.base_url = base_url or config.SENSENOVA_BASE_URL

    def _chat(self, api_key: str, prompt: str, timeout: float = 15.0) -> str:
        client = OpenAI(api_key=api_key, base_url=self.base_url, timeout=timeout)
        resp = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,  # 评论要有点随机性
            max_tokens=140,
            reasoning_effort="none",
            response_format={"type": "json_object"},
        )
        c = resp.choices[0].message.content
        if not c:
            raise ValueError("empty comment")
        return c

    def decide(self, snapshot: dict) -> dict | None:
        """决定是否说话。返回 None 表示（LLM 判定）不说话或链路失败。"""
        prompt = self._build_prompt(snapshot)
        for _ in range(2):
            idx, key = self.picker.next()
            try:
                text = self._chat(key, prompt)
            except Exception as e:  # noqa: BLE001
                logger.warning("comment LLM error: %s", e)
                self.picker.report_failure(idx)
                continue
            self.picker.report_success(idx)
            try:
                data = json.loads(text)
            except Exception:  # noqa: BLE001
                continue
            if not data.get("should_comment"):
                return None
            speaker = str(data.get("speaker", "")).strip()
            text = str(data.get("text", "")).strip()
            if speaker and text:
                return {"speaker": speaker, "text": text}
        return None

    def _build_prompt(self, snap: dict) -> str:
        lines = [
            "你是斗地主大厅的评论区主持人，负责在牌局的关键时刻插一句有节目效果的评论。",
            "下列「局面事件」来自本局最近的动向，请判断是否值得因此说一两句话。",
            f"事件：{snap.get('event_desc')}",
            f"发言人候选（必须是名单里的人，选一个最贴切的）：{' / '.join(snap.get('names'))}",
            f"不必每次都说话；觉得没意思就 should_comment=false。",
            '只输出 JSON：{"should_comment": true/false, "speaker": "名字", "text": "一句中文评论"}',
            "text 要口语、简短（≤35 字），可以毒舌也可以提醒。",
        ]
        return "\n".join(lines)