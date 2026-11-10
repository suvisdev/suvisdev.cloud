"""`.env.example`에 문서화된 키가 실제 `.env`에 있는지 비교한다.

`RECOMMENDATION_BACKEND`가 `.env.example`엔 2026-08-03부터 문서화돼 있었는데
EC2 `.env`엔 반영된 적이 없어, 배포 환경이 의도와 다른 백엔드로 돌던 사고
(WORK_LOG 2026-08-05)의 재발 방지. 같은 패턴이 `EMBEDDING_BACKEND`에서도
반복될 수 있다(2026-08-07 신설).

**값은 비교하지 않는다** — 비밀번호·API 키가 로그·CI 출력에 새면 안 되므로
키 이름의 존재 여부만 본다.

`KEY=` 형태도 주석도 아닌 **깨진 줄**도 함께 잡는다(2026-08-10 신설). 편집기
확장이 열린 파일에 단독 `1` 문자를 끼워 넣는 사고가 세 번 반복됐고
(2026-07-29·07-30·08-04), 2026-08-10엔 로컬·EC2 `.env` 29번째 줄
(`GEMINI_API_KEY` 바로 다음)에 실제로 남아 있는 것을 발견했다. 조용히
방치되는 게 문제라 탐지 대상에 넣는다.

`--code`는 반대 방향을 본다(2026-11-10 신설): 코드가 `os.getenv("KEY")` 등으로 읽는 키가
`.env.example`에 있는지. `.env` 없이 돌아 CI에서 쓴다. 기존 누락은 `_UNDOCUMENTED_BASELINE`에 두고
**새 누락만** 실패시킨다. 명단의 키를 문서화하거나 코드에서 지우면 명단에서도 지워야 통과한다(줄이기만).

Usage (suvisdev 폴더에서):
  python scripts/check_env_drift.py
  python scripts/check_env_drift.py --env .env --example .env.example
  python scripts/check_env_drift.py --code

종료 코드: 누락 키가 있으면 1, 없으면 0 (CI·배포 스크립트에서 게이트로 쓸 수 있다).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# `.env.example`은 대부분의 키를 주석 처리해 문서화한다(`# FOO=bar`) — 주석 여부와
# 무관하게 "문서화된 키"로 센다.
_EXAMPLE_KEY = re.compile(r"^\s*#?\s*([A-Z][A-Z0-9_]*)\s*=")
_ENV_KEY = re.compile(r"^\s*([A-Z][A-Z0-9_]*)\s*=")
_CODE_KEY = re.compile(
    r"""os\.(?:getenv|environ\.get|environ\.setdefault)\(\s*["']([A-Z][A-Z0-9_]+)["']"""
    r"""|os\.environ\[\s*["']([A-Z][A-Z0-9_]+)["']\s*\]"""
)
_CODE_ROOTS = ("apps", "core", "shared")

# 11-10 실측 기존 누락 39개 — 줄이기만 한다. 새 키는 여기 넣지 말고 .env.example에 문서화한다.
_UNDOCUMENTED_BASELINE = frozenset(
    {
        "DISCORD_WEBHOOK_URL",
        "EDITOR_REVIEWS_DAILY_LIMIT",
        "EDITOR_REVIEWS_STATE",
        "ENABLE_MOVA_STARTUP",
        "GEMINI_EMBED_MODEL",
        "GILDLE_CSV_ENCODING",
        "GILDLE_DB_MODE",
        "GILDLE_ELEVATION_JSON",
        "GILDLE_GRAPH_CACHE_DIR",
        "GILDLE_HAZARD_CSV",
        "GILDLE_ORCHESTRATOR_MODEL",
        "GILDLE_ORCHESTRATOR_TIMEOUT_S",
        "GILDLE_OSM_CENTER_LAT",
        "GILDLE_OSM_CENTER_LNG",
        "GILDLE_OSM_DIST_M",
        "GILDLE_SCORED_EDGES",
        "GILDLE_SHADE_SCORES",
        "GILDLE_TREE_CSV",
        "GILDLE_UNDERSTANDING",
        "GILDLE_WALK_GRAPH",
        "INFERENCE_URL",
        "JWT_PRIVATE_KEY_B64",
        "MOVA_AGENT_MODEL",
        "MOVA_AGENT_TIMEOUT_S",
        "MOVA_CHAT_AGENT",
        "MOVA_SHADOW_LOG",
        "NODE_NAME",
        "OLLAMA_EMBED_MODEL",
        "OLLAMA_KEEP_ALIVE",
        "REDIS_URL",
        "SENTIMENT_BATCH_LIMIT",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
        "VIEWER_ADMIN_EMAIL",
        "VIEWER_ADMIN_NICKNAME",
        "VIEWER_ADMIN_PASSWORD",
        "VIEWER_ADMIN_USERNAME",
        "VIEWER_DATABASE_URL",
        "VWORLD_API_KEY",
    }
)


def _keys(path: Path, pattern: re.Pattern[str]) -> set[str]:
    return {
        m.group(1)
        for line in path.read_text(encoding="utf-8").splitlines()
        if (m := pattern.match(line))
    }


def _malformed_lines(path: Path) -> list[tuple[int, str]]:
    """`KEY=`도 주석도 빈 줄도 아닌 줄 → (줄번호, 내용).

    `export FOO=bar`처럼 정당하지만 `_ENV_KEY`에 안 걸리는 형태가 있어 그건 통과시킨다.
    """
    out: list[tuple[int, str]] = []
    for no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if _ENV_KEY.match(line) or _ENV_KEY.match(stripped.removeprefix("export ")):
            continue
        out.append((no, stripped))
    return out


def _code_keys(base: Path) -> dict[str, str]:
    """코드(테스트 제외)가 읽는 환경 변수 → 처음 발견한 파일."""
    files = [p for root in _CODE_ROOTS for p in sorted((base / root).rglob("*.py"))]
    files.append(base / "main.py")
    found: dict[str, str] = {}
    for path in files:
        if {"tests", "test"} & set(path.parts) or not path.is_file():
            continue
        for m in _CODE_KEY.finditer(path.read_text(encoding="utf-8", errors="ignore")):
            found.setdefault(m.group(1) or m.group(2), str(path.relative_to(base)))
    return found


def check_code(example_path: Path, base: Path = Path()) -> int:
    documented = _keys(example_path, _EXAMPLE_KEY)
    used = _code_keys(base)
    new = sorted(k for k in used if k not in documented and k not in _UNDOCUMENTED_BASELINE)
    stale = sorted(k for k in _UNDOCUMENTED_BASELINE if k in documented or k not in used)
    for key in new:
        print(f"[env-code] {used[key]}가 읽는 {key}가 .env.example에 없습니다 — 문서화하세요.")
    for key in stale:
        print(
            f"[env-code] {key}는 이제 문서화됐거나 안 쓰입니다 — _UNDOCUMENTED_BASELINE에서 지우세요."
        )
    if new or stale:
        return 1
    print(
        f"[env-code] 새 누락 없음 (코드 키 {len(used)}개, 기존 누락 {len(_UNDOCUMENTED_BASELINE)}개)"
    )
    return 0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", default=".env")
    parser.add_argument("--example", default=".env.example")
    parser.add_argument("--code", action="store_true", help="코드가 읽는 키가 문서화됐는지 본다")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.code:
        return check_code(Path(args.example))
    env_path, example_path = Path(args.env), Path(args.example)

    for p in (env_path, example_path):
        if not p.is_file():
            print(f"[env-drift] 파일이 없습니다: {p}")
            return 1

    documented = _keys(example_path, _EXAMPLE_KEY)
    actual = _keys(env_path, _ENV_KEY)

    malformed = _malformed_lines(env_path)
    if malformed:
        print(f"[env-drift] {env_path}에 KEY=VALUE도 주석도 아닌 줄 {len(malformed)}개:")
        for no, text in malformed:
            # 값이 아니라 깨진 줄 자체라 그대로 보여준다(비밀이 들어갈 자리가 아니다).
            print(f"  - {no}행: {text!r}")
        print(
            "[env-drift] 편집기 확장이 끼워 넣은 문자일 수 있다(WORK_LOG 2026-07-29·07-30·08-04·08-10)."
        )

    missing = sorted(documented - actual)
    undocumented = sorted(actual - documented)

    if undocumented:
        # 실패 사유는 아니다 — .env에만 있는 키는 실험용·환경 전용일 수 있다.
        print(
            f"[env-drift] .env.example에 없는 키 {len(undocumented)}개(참고): {', '.join(undocumented)}"
        )

    if missing:
        print(f"[env-drift] .env에 없는 키 {len(missing)}개:")
        for key in missing:
            print(f"  - {key}")
        print("[env-drift] 값이 필요 없는 키면 무시해도 되지만, 배포 환경이 기본값으로")
        print("            도는 걸 의도했는지 확인할 것(RECOMMENDATION_BACKEND 사고 참고).")
        return 1

    if malformed:
        return 1

    print(f"[env-drift] 누락 없음 (문서화 {len(documented)}개 전부 존재)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
