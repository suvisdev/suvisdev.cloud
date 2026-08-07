"""`.env.example`에 문서화된 키가 실제 `.env`에 있는지 비교한다.

`RECOMMENDATION_BACKEND`가 `.env.example`엔 2026-08-03부터 문서화돼 있었는데
EC2 `.env`엔 반영된 적이 없어, 배포 환경이 의도와 다른 백엔드로 돌던 사고
(WORK_LOG 2026-08-05)의 재발 방지. 같은 패턴이 `EMBEDDING_BACKEND`에서도
반복될 수 있다(2026-08-07 신설).

**값은 비교하지 않는다** — 비밀번호·API 키가 로그·CI 출력에 새면 안 되므로
키 이름의 존재 여부만 본다.

Usage (suvisdev 폴더에서):
  python scripts/check_env_drift.py
  python scripts/check_env_drift.py --env .env --example .env.example

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


def _keys(path: Path, pattern: re.Pattern[str]) -> set[str]:
    return {
        m.group(1)
        for line in path.read_text(encoding="utf-8").splitlines()
        if (m := pattern.match(line))
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", default=".env")
    parser.add_argument("--example", default=".env.example")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    env_path, example_path = Path(args.env), Path(args.example)

    for p in (env_path, example_path):
        if not p.is_file():
            print(f"[env-drift] 파일이 없습니다: {p}")
            return 1

    documented = _keys(example_path, _EXAMPLE_KEY)
    actual = _keys(env_path, _ENV_KEY)

    missing = sorted(documented - actual)
    undocumented = sorted(actual - documented)

    if undocumented:
        # 실패 사유는 아니다 — .env에만 있는 키는 실험용·환경 전용일 수 있다.
        print(f"[env-drift] .env.example에 없는 키 {len(undocumented)}개(참고): {', '.join(undocumented)}")

    if missing:
        print(f"[env-drift] .env에 없는 키 {len(missing)}개:")
        for key in missing:
            print(f"  - {key}")
        print("[env-drift] 값이 필요 없는 키면 무시해도 되지만, 배포 환경이 기본값으로")
        print("            도는 걸 의도했는지 확인할 것(RECOMMENDATION_BACKEND 사고 참고).")
        return 1

    print(f"[env-drift] 누락 없음 (문서화 {len(documented)}개 전부 존재)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
