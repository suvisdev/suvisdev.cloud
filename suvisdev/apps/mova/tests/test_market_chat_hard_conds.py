"""_hard_conds 언어 허용목록 정책 유닛 테스트.

국가 미명시 요청에는 ko·en 허용목록이 걸리고, 국가를 명시한 요청
("일본 애니메이션")에는 허용목록이 빠져야 한다 — 2026-08-26 프로덕션에서
JP 요청이 언어 필터에 걸려 recs=0 되던 실측 버그의 회귀 방지.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))  # core.* 임포트용

from mova.adapter.outbound.pg.market_chat_pg_repository import ChatPgRepository  # noqa: E402


def _conds_sql(countries: list[str] | None) -> str:
    repo = ChatPgRepository(session=None)  # _hard_conds는 세션을 쓰지 않는다
    conds = repo._hard_conds(countries, None, None)
    return " ".join(str(c) for c in conds)


class HardCondsLanguagePolicyTests(unittest.TestCase):
    def test_no_country_applies_language_allowlist(self) -> None:
        sql = _conds_sql(None)
        self.assertIn("original_language", sql)

    def test_explicit_country_bypasses_language_allowlist(self) -> None:
        sql = _conds_sql(["JP"])
        self.assertNotIn("original_language", sql)
        self.assertIn("origin_country", sql)


if __name__ == "__main__":
    unittest.main()
