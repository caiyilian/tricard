"""SocketIO 握手冒烟脚本（阶段0 验收）：连接服务器 → 发 ping → 等 pong。"""

import sys
import time

import socketio

SIO_CLIENT = socketio.Client(logger=False, engineio_logger=False)


def main(url: str = "http://127.0.0.1:8000") -> int:
    received = {}

    @SIO_CLIENT.event
    def connect():
        print("[connected]")

    @SIO_CLIENT.event
    def pong(data):
        received["pong"] = data
        print(f"[pong] {data}")

    print(f"connecting to {url} ...")
    SIO_CLIENT.connect(url, wait_timeout=5)
    SIO_CLIENT.emit("ping", {"hello": "tricard"})
    deadline = time.time() + 5
    while "pong" not in received and time.time() < deadline:
        SIO_CLIENT.sleep(0.1)
    SIO_CLIENT.disconnect()

    if "pong" in received:
        print("SMOKE OK: socketio handshake works")
        return 0
    print("SMOKE FAIL: no pong received")
    return 1


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    sys.exit(main(url))