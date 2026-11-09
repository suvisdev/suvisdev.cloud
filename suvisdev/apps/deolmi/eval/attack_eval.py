"""덜미 공격 시험 — 쉬운 매크로부터 사람 흉내까지 단계별 판정을 잰다.

대상은 attack_server.py 임시 서버(localhost)뿐이다. 다른 주소는 거부한다.
결과는 표로 출력하고 --save 경로에 JSON으로 남긴다.
"""

from __future__ import annotations

import argparse
import json
import random
import time
import urllib.error
import urllib.request
from collections import Counter
from collections.abc import Callable
from statistics import median
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import Page, sync_playwright

SITE_KEY, SECRET = "pk_eval", "sk_eval"

# 사람이 낼 법한 값을 손으로 적은 것. 브라우저도 SDK도 쓰지 않는다.
FORGED: dict[str, float] = {
    "move_count": 180,
    "path_px": 2400,
    "straightness": 0.62,
    "click_count": 2,
    "click_iv_mean": 3200,
    "click_iv_std": 0,
    "key_count": 14,
    "key_iv_std": 85,
    "dwell_ms": 14000,
    "touch_count": 0,
    "kbd_click_count": 0,
}


def _post(
    base: str, path: str, body: dict[str, Any], origin: str | None = None
) -> tuple[int, dict[str, Any]]:
    headers = {"Content-Type": "application/json"}
    if origin:
        headers["Origin"] = origin  # 브라우저 밖 프로그램은 이 헤더를 마음대로 넣는다
    req = urllib.request.Request(base + path, json.dumps(body).encode(), headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return res.status, json.load(res)
    except urllib.error.HTTPError as e:
        return e.code, {}


def _verify(base: str, token: str) -> dict[str, Any]:
    status, body = _post(base, "/api/deolmi/verify", {"secret": SECRET, "token": token})
    if status != 200:
        raise RuntimeError(f"verify HTTP {status}")
    return body


def _raw(base: str, signals: dict[str, float]) -> dict[str, Any]:
    status, issued = _post(
        base, "/api/deolmi/score", {"site_key": SITE_KEY, "signals": signals}, origin=base
    )
    if status != 200:
        raise RuntimeError(f"score HTTP {status}")
    return _verify(base, issued["token"])


def _center(page: Page, selector: str) -> tuple[float, float]:
    box = page.locator(selector).bounding_box()
    assert box is not None
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


def _curve_to(page: Page, start: tuple[float, float], end: tuple[float, float]) -> None:
    """곡선 경로 + 떨림 + 불규칙한 속도로 마우스를 옮긴다."""
    bend = (
        (start[0] + end[0]) / 2 + random.uniform(-220, 220),
        (start[1] + end[1]) / 2 + random.uniform(-160, 160),
    )
    steps = random.randint(25, 55)
    for i in range(1, steps + 1):
        t = i / steps
        x = (1 - t) ** 2 * start[0] + 2 * (1 - t) * t * bend[0] + t**2 * end[0]
        y = (1 - t) ** 2 * start[1] + 2 * (1 - t) * t * bend[1] + t**2 * end[1]
        page.mouse.move(x + random.gauss(0, 1.5), y + random.gauss(0, 1.5))
        page.wait_for_timeout(max(1, random.gauss(9, 5)))


def _plain(page: Page) -> None:
    page.fill("#name", "홍길동")
    page.fill("#phone", "01012345678")
    page.click("#seat")
    page.click("#buy")


def _fixed_typing(page: Page) -> None:
    page.click("#seat")
    page.click("#name")
    page.keyboard.type("hong gildong", delay=60)
    page.click("#phone")
    page.keyboard.type("01012345678", delay=60)
    page.click("#buy")


def _linear_mouse(page: Page) -> None:
    page.mouse.move(5, 5)
    for selector in ("#seat", "#name", "#phone", "#buy"):
        page.mouse.move(*_center(page, selector), steps=30)
        page.mouse.down()
        page.mouse.up()
        if selector == "#name":
            page.keyboard.type("hong gildong", delay=random.randint(50, 200))
        if selector == "#phone":
            page.keyboard.type("01012345678", delay=random.randint(50, 200))


def _humanized(page: Page) -> None:
    position = (random.uniform(50, 600), random.uniform(30, 300))
    page.mouse.move(*position)
    page.wait_for_timeout(random.uniform(500, 1500))
    for selector, text in (
        ("#seat", ""),
        ("#name", "hong gildong"),
        ("#phone", "01012345678"),
        ("#buy", ""),
    ):
        target = _center(page, selector)
        _curve_to(page, position, target)
        position = target
        page.wait_for_timeout(random.uniform(120, 500))
        page.mouse.down()
        page.wait_for_timeout(random.uniform(40, 120))
        page.mouse.up()
        for ch in text:
            page.keyboard.type(ch)
            page.wait_for_timeout(max(20, random.gauss(120, 55)))
        page.wait_for_timeout(random.uniform(200, 900))


def _tuned(page: Page) -> None:
    """코드가 공개돼 있으니 모델 표본 범위에 맞춘다: Tab 으로 칸을 옮겨 간격 편차를 낮춘다."""
    position = (random.uniform(50, 300), random.uniform(30, 200))
    page.mouse.move(*position)
    for _ in range(random.randint(3, 4)):  # 표본 수준의 이동 거리 채우기
        target = (random.uniform(100, 1200), random.uniform(50, 850))
        _curve_to(page, position, target)
        position = target
    page.wait_for_timeout(random.uniform(1500, 3000))
    for selector in ("#seat", "#name"):
        target = _center(page, selector)
        _curve_to(page, position, target)
        position = target
        page.wait_for_timeout(random.uniform(300, 700))
        page.mouse.down()
        page.mouse.up()
    for text in ("hong gildong", "01012345678"):
        for ch in text:
            page.keyboard.type(ch)
            page.wait_for_timeout(max(30, random.gauss(120, 70)))
        page.keyboard.press("Tab")
        page.wait_for_timeout(max(30, random.gauss(120, 70)))
    _curve_to(page, position, _center(page, "#buy"))
    page.mouse.down()
    page.mouse.up()


BROWSER_LEVELS: dict[str, Callable[[Page], None]] = {
    "B1 기본 자동화(fill·click)": _plain,
    "B2 고정 간격 타자": _fixed_typing,
    "B3 직선 마우스·랜덤 타자": _linear_mouse,
    "B4 곡선 마우스·사람 흉내": _humanized,
    "B5 모델 표본에 맞춘 흉내": _tuned,
}


def _summary(name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    verdicts = Counter(r["verdict"] for r in rows)
    reasons = Counter(reason for r in rows for reason in r.get("reasons", []))
    return {
        "level": name,
        "n": len(rows),
        "allow": verdicts["allow"],
        "challenge": verdicts["challenge"],
        "block": verdicts["block"],
        "score_median": round(median(r["score"] for r in rows), 3),
        "top_reason": reasons.most_common(1)[0][0] if reasons else "",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:8321")
    parser.add_argument("-n", type=int, default=15)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--save", default=None)
    args = parser.parse_args()
    if urlparse(args.base).hostname != "localhost":
        raise SystemExit("이 도구는 localhost 임시 서버만 시험한다")
    random.seed(args.seed)

    no_origin, _ = _post(args.base, "/api/deolmi/score", {"site_key": SITE_KEY, "signals": FORGED})
    print(f"A0 Origin 헤더 없이 직접 호출: HTTP {no_origin}")
    out: list[dict[str, Any]] = []
    empty = [_raw(args.base, {}) for _ in range(args.n)]
    out.append(_summary("A1 API 직접 호출(빈 신호)", empty))
    time.sleep(11)  # 앞 단계 속도 창이 판정에 섞이지 않게
    forged = []
    for _ in range(args.n):
        signals = {k: v * random.uniform(0.8, 1.2) for k, v in FORGED.items()}
        signals["straightness"] = min(signals["straightness"], 0.9)
        for count in ("move_count", "click_count", "key_count"):
            signals[count] = int(signals[count])
        signals["click_count"] = 2
        signals["click_iv_std"] = 0
        forged.append(_raw(args.base, signals))
    out.append(_summary("A2 API 직접 호출(지어낸 사람 신호)", forged))
    time.sleep(11)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, attack in BROWSER_LEVELS.items():
            rows = []
            for _ in range(args.n):
                page = browser.new_page(viewport={"width": 1280, "height": 900})
                page.goto(args.base + "/page")
                attack(page)
                page.wait_for_function("window.__result !== undefined", timeout=20000)
                result = page.evaluate("window.__result")
                rows.append({**_verify(args.base, result["token"]), "signals": result["signals"]})
                page.close()
                time.sleep(0.6)  # 같은 IP 속도 신호를 빼고 행동 신호만 잰다
            out.append(_summary(name, rows))
        browser.close()

    time.sleep(11)
    burst = [_raw(args.base, dict(FORGED)) for _ in range(80)]
    out.append(_summary("A3 지어낸 신호 80회 연속", burst[-20:]))

    for row in out:
        print(
            f"{row['level']:<30} n={row['n']:<3} 통과 {row['allow']:<3} 확인 {row['challenge']:<3} "
            f"차단 {row['block']:<3} 중앙값 {row['score_median']:<6} {row['top_reason']}"
        )
    if args.save:
        with open(args.save, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
