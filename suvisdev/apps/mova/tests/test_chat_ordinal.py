"""서수 지시어 치환 — 추천 카드 목록을 가리키는 "두번째꺼" 등(2026-09-28 실사용)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
for _p in (_ROOT, _ROOT / "apps"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from mova.app.use_cases.market_chat_ordinal import resolve_ordinal_reference  # noqa: E402

_CARDS = (
    "[추천 카드] 1.『바람피기 좋은 날』(2007) 2.『비와 당신의 이야기』(2021) 3.『한강에게』(2019)\n"
    "비 오는 날의 분위기에 어울리는 영화들을 준비했습니다."
)
_HIST = [
    {"role": "user", "content": "비 오는 날 어울리는 영화"},
    {"role": "assistant", "content": _CARDS},
]


class OrdinalTests(unittest.TestCase):
    def test_ordinals_resolve_to_card_titles(self) -> None:
        for msg, want in (
            ("두번째꺼 어디서 볼 수 있어", "비와 당신의 이야기 어디서 볼 수 있어"),
            ("두 번째 거 어때?", "비와 당신의 이야기 어때?"),
            ("첫번째 영화 줄거리 알려줘", "바람피기 좋은 날 줄거리 알려줘"),
            ("3번 예매하고 싶어", "한강에게 예매하고 싶어"),
            ("마지막꺼 평점은?", "한강에게 평점은?"),
            ("셋째 어때", "한강에게 어때"),
        ):
            self.assertEqual(resolve_ordinal_reference(msg, _HIST), want, msg)

    def test_no_rewrite_without_cards_or_out_of_range(self) -> None:
        plain = [{"role": "assistant", "content": "비 오는 날 영화들을 준비했습니다."}]
        self.assertIsNone(resolve_ordinal_reference("두번째꺼 어때", plain))
        self.assertIsNone(resolve_ordinal_reference("다섯번째꺼 어때", _HIST))  # 카드 3장
        self.assertIsNone(resolve_ordinal_reference("1번 더 추천해줘", _HIST))
        self.assertIsNone(resolve_ordinal_reference("마지막으로 하나만 추천해줘", _HIST))
        self.assertIsNone(resolve_ordinal_reference("인턴 어때", _HIST))


if __name__ == "__main__":
    unittest.main()
