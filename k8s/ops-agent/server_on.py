"""전체 끄기 뒤 서버를 다시 켠다. 어드민을 쓸 수 없을 때 노트북 바탕화면 '서버 켜기'가 부른다."""

import json
import os
import sys
import time
import urllib.error
import urllib.request

URL = "http://127.0.0.1:8210"
ENV_FILE = os.path.expanduser("~/.config/ops-agent/env")


def read_token(env_text: str) -> str:
    for line in env_text.splitlines():
        key, _, value = line.partition("=")
        if key.strip() == "OPS_AGENT_TOKEN":
            return value.strip()
    return ""


def call(path: str, token: str, post: bool = False) -> dict:
    req = urllib.request.Request(
        URL + path,
        data=b"" if post else None,
        headers={"X-Ops-Token": token},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main() -> int:
    with open(ENV_FILE, encoding="utf-8") as f:
        token = read_token(f.read())
    try:
        print("켜는 중입니다. 집컴 → 노트북 순서라 몇 분 걸릴 수 있습니다.")
        call("/server/start", token, post=True)
        while True:
            time.sleep(5)
            job = call("/status", token)["job"]
            if job["state"] != "running":
                break
    except urllib.error.HTTPError as e:
        print("실패:", json.load(e).get("error", e.code))
        return 1
    except urllib.error.URLError as e:
        print(
            "제어 에이전트에 닿지 않습니다(systemctl --user status ops-agent):",
            e.reason,
        )
        return 1
    if job["state"] == "ok":
        print("켜졌습니다.")
        return 0
    print("실패:", job["error"])
    return 1


if __name__ == "__main__":
    sys.exit(main())
