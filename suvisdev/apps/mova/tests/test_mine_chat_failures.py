"""scripts/mine_chat_failures.py — 규칙 판정(detect_turn)·대화 턴 조립·섀도 필터 유닛 테스트."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.mine_chat_failures import (  # noqa: E402
    detect_turn,
    mine_conversation,
    mine_shadow,
    render_assistant,
)

_SPIDER_HISTORY = [
    {"role": "user", "content": "스파이더맨 시리즈 추천해줘"},
    {
        "role": "assistant",
        "content": "[추천 카드] 1.『스파이더맨』(2002) 2.『스파이더맨: 브랜드 뉴 데이』(2026)\n추천해 드립니다.",
    },
]


class DetectTurnTests(unittest.TestCase):
    def test_zero_after_cards_is_context_failure(self) -> None:
        # 2026-09-28 실사용: "제일 최신 스파이더맨이 뭐야" → 0건
        rules = detect_turn(
            _SPIDER_HISTORY,
            "제일 최신 스파이더맨이 뭐야",
            "요청하신 조건과 겹치는 작품이 카탈로그에 없어요. 예: ...",
            None,
        )
        self.assertEqual(rules, ["zero_with_context"])

    def test_zero_without_context(self) -> None:
        rules = detect_turn(
            [], "외계 좀비 뮤지컬", "이 조건에는 매칭되는 작품이 안 잡히네요.", None
        )
        self.assertEqual(rules, ["zero_result"])

    def test_reask_on_deictic_with_context(self) -> None:
        rules = detect_turn(
            _SPIDER_HISTORY, "두번째꺼 예매", "어떤 작품을 예매하실지 제목을 알려주시겠어요?", None
        )
        self.assertIn("reask_with_context", rules)

    def test_reask_without_deictic_is_not_flagged(self) -> None:
        rules = detect_turn(_SPIDER_HISTORY, "예매", "어떤 작품을 예매하실지 알려주시겠어요?", None)
        self.assertNotIn("reask_with_context", rules)

    def test_user_correction_and_repeat(self) -> None:
        self.assertEqual(
            detect_turn([], "공포 추천", "『파묘』 어떠세요", "아니 그거 말고 외국 공포"),
            ["user_correction"],
        )
        self.assertEqual(
            detect_turn([], "제일 최신 스파이더맨 뭐야", "…", "제일 최신 스파이더맨이 뭐야"),
            ["user_correction"],
        )

    def test_normal_turn_has_no_rules(self) -> None:
        rules = detect_turn(
            _SPIDER_HISTORY, "그거 줄거리 알려줘", "모두의 기억 속에서 사라진 피터 파커가…", "좋네"
        )
        self.assertEqual(rules, [])


class MineConversationTests(unittest.TestCase):
    def test_history_carries_cards_into_next_turn(self) -> None:
        rows = [
            {"role": "user", "content": "스파이더맨 시리즈 추천해줘", "meta": {}},
            {
                "role": "assistant",
                "content": "추천해 드립니다.",
                "meta": {
                    "recommendations": [{"title": "스파이더맨: 브랜드 뉴 데이", "year": 2026}]
                },
            },
            {
                "role": "user",
                "content": "제일 최신 스파이더맨이 뭐야",
                "meta": {"intent_type": "mood"},
            },
            {
                "role": "assistant",
                "content": "요청하신 조건과 겹치는 작품이 카탈로그에 없어요.",
                "meta": {},
            },
        ]
        out = mine_conversation(7, rows)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["rules"], ["zero_with_context"])
        self.assertEqual(out[0]["conversation_id"], 7)
        self.assertEqual(out[0]["intent_type"], "mood")
        self.assertIn("『스파이더맨: 브랜드 뉴 데이』(2026)", out[0]["history"][-1]["content"])

    def test_render_assistant_without_cards_is_plain(self) -> None:
        self.assertEqual(render_assistant("안녕하세요", {}), "안녕하세요")


class MineShadowTests(unittest.TestCase):
    def test_only_mismatches(self) -> None:
        records = [
            {"message": "a", "match": True},
            {"message": "b", "match": False, "diff": ["title"]},
        ]
        out = mine_shadow(records)
        self.assertEqual([r["message"] for r in out], ["b"])
        self.assertEqual(out[0]["rules"], ["shadow_diff"])


if __name__ == "__main__":
    unittest.main()
