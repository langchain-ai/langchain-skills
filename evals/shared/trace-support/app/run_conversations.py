"""Start the tools service, play the recorded conversations, then stop the service."""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from assistant import TOOLS_URL, handle_turn

HERE = Path(__file__).resolve().parent


def wait_until_ready(timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{TOOLS_URL}/health", timeout=1):
                return
        except (urllib.error.URLError, ConnectionError):
            time.sleep(0.2)
    raise RuntimeError("tools service did not start")


def stop_service(process: subprocess.Popen) -> None:
    try:
        urllib.request.urlopen(urllib.request.Request(f"{TOOLS_URL}/shutdown", data=b"", method="POST"), timeout=5)
        process.wait(timeout=15)
    except (urllib.error.URLError, ConnectionError, subprocess.TimeoutExpired):
        process.terminate()
        process.wait(timeout=5)


def main() -> None:
    conversations = json.loads((HERE / "conversations.json").read_text())
    service = subprocess.Popen([sys.executable, str(HERE / "tools_service.py")], cwd=HERE)
    try:
        wait_until_ready()
        for conversation in conversations:
            history: list[dict] = []
            print(f"== {conversation['id']}")
            for message in conversation["turns"]:
                reply = handle_turn(conversation["id"], history, message)
                print(f"user: {message}\nassistant: {reply}")
                history += [{"role": "user", "content": message}, {"role": "assistant", "content": reply}]
    finally:
        stop_service(service)


if __name__ == "__main__":
    main()
