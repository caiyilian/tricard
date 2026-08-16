"""SenseNova API 诊断脚本。

用途：游戏出问题、怀疑是 LLM 层导致时，先跑本脚本初步排查：
1. 7 个账号是否都正常（能出牌、能解析 JSON、返回速度）
2. 指定模型是否可用（默认 sensenova-6.8-flash-lite）

用法：
    uv run python backend/scripts/llm_api_test.py                # 全量 7 key 诊断
    uv run python backend/scripts/llm_api_test.py --model deepseek-v4-flash
    uv run python backend/scripts/llm_api_test.py --keys-file path/to/keys.txt
"""

import argparse
import json
import sys
import time
from pathlib import Path

from openai import OpenAI

BASE_URL = "https://token.sensenova.cn/v1"
DEFAULT_MODEL = "sensenova-6.8-flash-lite"
DEFAULT_KEYS_FILE = Path(__file__).resolve().parents[2] / "sensenova_apikey.txt"

PROMPT = (
    "你是斗地主 AI，现在轮到你出牌。你的手牌：[3, 4, 小王]，上家出牌：3，"
    "必须压过上家的单张。只输出 JSON，不要任何其他文字："
    '{"action": "play", "cards": ["4"]}'
)


def load_keys(path: Path) -> list[str]:
    if not path.exists():
        print(f"ERROR: keys file not found: {path}")
        sys.exit(2)
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def call_once(key: str, model: str, timeout: float = 30.0) -> tuple[bool, str, float]:
    client = OpenAI(api_key=key, base_url=BASE_URL, timeout=timeout)
    t0 = time.perf_counter()
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": PROMPT}],
            temperature=0.7,
            max_tokens=120,
            reasoning_effort="none",
            response_format={"type": "json_object"},
        )
        elapsed = time.perf_counter() - t0
        content = resp.choices[0].message.content
        if not content:
            return False, f"empty content (finish={resp.choices[0].finish_reason})", elapsed
        parsed = json.loads(content)
        return True, f"OK action={parsed.get('action')} cards={parsed.get('cards')}", elapsed
    except Exception as e:  # noqa: BLE001
        elapsed = time.perf_counter() - t0
        return False, f"FAIL {type(e).__name__}: {e}", elapsed


def main() -> int:
    parser = argparse.ArgumentParser(description="SenseNova API diagnostic")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"model id (default: {DEFAULT_MODEL})")
    parser.add_argument("--keys-file", type=Path, default=DEFAULT_KEYS_FILE, help="path to api keys file")
    parser.add_argument("--keys-cap", type=int, default=None, help="only test first N keys (default: all)")
    args = parser.parse_args()

    keys = load_keys(args.keys_file)
    if args.keys_cap:
        keys = keys[: args.keys_cap]
    print(f"model={args.model} | keys={len(keys)} loaded from {args.keys_file.name}")

    ok = 0
    avg = 0.0
    for i, key in enumerate(keys, 1):
        masked = f"{key[:6]}...{key[-4:]}"
        success, info, elapsed = call_once(key, args.model)
        ok += int(success)
        avg += elapsed
        print(f"[{i}/{len(keys)}] {masked} -> {info} ({elapsed:.2f}s)")
    avg /= len(keys)
    print(f"RESULT: {ok}/{len(keys)} keys work, avg latency {avg:.2f}s")
    return 0 if ok == len(keys) else 1


if __name__ == "__main__":
    sys.exit(main())