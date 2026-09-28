"""에디터 리뷰 스케줄러 — 실패 영화 쿨다운으로 큐가 막히지 않게(2026-09-28 "생성 0/15")."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
for _p in (_ROOT, _ROOT / "apps"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from mova.adapter.inbound.scheduler import editor_reviews_scheduler as m  # noqa: E402


class EditorReviewSkipTests(unittest.TestCase):
    def test_skipped_movies_are_passed_over_until_cooldown_ends(self) -> None:
        now = 1_000_000_000.0
        state = {"skips": {"1": now - 3600, "2": now - 31 * 86_400}}  # 1은 쉬는 중, 2는 쿨다운 끝
        skips = m.active_skips(state, now)
        self.assertEqual(set(skips), {"1"})
        pool = [
            (1, "라이즈", 2024),
            (2, "플래닛", 2023),
            (3, "크리에이터", 2023),
            (4, "아웃핏", 2022),
        ]
        self.assertEqual([p[0] for p in m.pick_candidates(pool, skips, 2)], [2, 3])

    def test_state_round_trip(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            old = m._STATE_PATH
            m._STATE_PATH = Path(d) / "s.json"
            try:
                self.assertEqual(m._load_state(), {"last_cycle": 0, "skips": {}})
                m._save_state({"last_cycle": 5, "skips": {"9": 1.0}})
                self.assertEqual(m._load_state()["skips"], {"9": 1.0})
            finally:
                m._STATE_PATH = old


if __name__ == "__main__":
    unittest.main()
