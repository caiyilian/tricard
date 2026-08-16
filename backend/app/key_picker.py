"""SenseNova API Key 轮询调度。

规则：
- 每次调用均匀轮询到下一个 key（7 个轮转，不用完一个再换下一个），适配 5 小时滚动窗口
- 某 key 失败（429/额度不足/网络错）→ 临时禁用一段时间，超时后自动恢复参与轮询
- 线程安全（Room 并发时可能多个座位同时调）
"""

import threading
import time


class KeyPicker:
    def __init__(self, keys: list[str], cool_down: float = 60.0):
        if not keys:
            raise ValueError("at least one api key required")
        self.keys = list(keys)
        self.cool_down = cool_down
        self._idx = 0
        self._disabled_until: dict[int, float] = {}
        self._lock = threading.Lock()

    def next(self) -> tuple[int, str]:
        """返回下一个可用 key 的 (index, key)。若全部暂不可用，返回当前轮到的那个兜底。"""
        now = time.time()
        with self._lock:
            n = len(self.keys)
            for _ in range(n):
                i = self._idx % n
                self._idx += 1
                if self._disabled_until.get(i, 0) <= now:
                    return i, self.keys[i]
            # 全部被禁：放宽，用轮到的第一个并清零其禁用
            i = (self._idx - 1) % n
            self._disabled_until.pop(i, None)
            return i, self.keys[i]

    def report_failure(self, index: int, cool_down: float | None = None) -> None:
        with self._lock:
            self._disabled_until[index] = time.time() + (cool_down or self.cool_down)

    def report_success(self, index: int) -> None:
        with self._lock:
            self._disabled_until.pop(index, None)

    @property
    def enabled_count(self) -> int:
        now = time.time()
        return sum(1 for v in self._disabled_until.values() if v <= now)