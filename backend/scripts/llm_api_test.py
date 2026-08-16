import json
import os
import sys
from pathlib import Path

from openai import OpenAI

BASE_URL = "https://token.sensenova.cn/v1"
MODEL = "sensenova-6.8-flash-lite"
KEYS_FILE = Path(__file__).resolve().parents[2] / "sensenova_apikey.txt"


def load_keys() -> list[str]:
    return [line.strip() for line in KEYS_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]


def call_once(key: str, timeout: float = 30.0) -> tuple[bool, str]:
    client = OpenAI(api_key=key, base_url=BASE_URL, timeout=timeout)
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "你是斗地主 AI，现在轮到你出牌。你的手牌：[3, 4, 小王]，上家出牌：3，"
                        "必须压过上家的单张。只输出 JSON，不要任何其他文字："
                        '{"action": "play", "cards": ["4"]}'
                    ),
                }
            ],
            temperature=0.7,
            max_tokens=120,
            reasoning_effort="none",
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content
        parsed = json.loads(content)
        return True, f"OK action={parsed.get('action')} cards={parsed.get('cards')}"
    except Exception as e:  # noqa: BLE001
        return False, f"FAIL {type(e).__name__}: {e}"


def main() -> int:
    keys = load_keys()
    print(f"loaded {len(keys)} keys from {KEYS_FILE.name}")
    ok = 0
    for i, key in enumerate(keys, 1):
        masked = f"sk-{key[3:7]}...{key[-4:]}"
        success, info = call_once(key)
        ok += int(success)
        print(f"[{i}/7] {masked} -> {info}")
    print(f"RESULT: {ok}/{len(keys)} keys work")
    return 0 if ok == len(keys) else 1


if __name__ == "__main__":
    sys.exit(main())