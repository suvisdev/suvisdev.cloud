"""Gemini를 교사로 EXAONE LoRA 재학습용 증류 데이터셋을 생성한다.

현재 프롬프트 계약(ChatPromptBuilder + movie_id 그라운딩)에 맞는
(prompt, completion) JSONL을 만든다 — 기존 export 스크립트는 completion에
movie_id가 없어(구형식) 재학습해도 그라운딩을 배울 수 없다.

실행 (로컬 backend 컨테이너 안):
  docker exec suvisdev-backend-1 python /suvisdev/datasets/gen_teacher_dataset.py
출력: /suvisdev/datasets/chat_teacher_dataset.jsonl (호스트 바인드 마운트)
"""

from __future__ import annotations

import asyncio
import json
import random
import sys
import time
from pathlib import Path

# 로컬 컨테이너 이미지의 구버전 코드 대신 /tmp/gen에 복사한 최신 소스를 우선한다.
for p in ("/suvisdev/apps", "/suvisdev", "/tmp/gen", "/tmp/gen/apps"):
    sys.path.insert(0, p)  # 마지막 insert가 최우선 — /tmp/gen/apps가 맨 앞

OUT = Path("/suvisdev/datasets/chat_teacher_dataset.jsonl")
SLEEP_SECONDS = 4.5  # Gemini 무료 티어 15req/min

MOVIE_QUERIES = [
    "로맨스 말고 설레는 영화",
    "클래식 명작 처음 보는 사람용",
    "비 오는 날 보기 좋은 영화",
    "긴장감 넘치는 스릴러 추천해줘",
    "가족이랑 같이 볼만한 영화",
    "눈물 쏙 빼는 감동 영화",
    "머리 식힐 때 보는 코미디",
    "90년대 클래식 명작",
    "한국 액션 영화 추천",
    "우주 배경 SF 영화",
    "타임루프 소재 영화",
    "실화 바탕 영화 추천해줘",
    "송강호 나오는 영화",
    "마동석 액션 영화",
    "톰 크루즈 영화 추천",
    "레오나르도 디카프리오 명작",
    "디즈니 애니메이션 추천",
    "지브리 스타일 감성 애니",
    "무서운데 잔인하지 않은 공포 영화",
    "좀비 영화 추천해줘",
    "히어로 영화 몰아보기",
    "법정 드라마 영화",
    "음악이 좋은 영화",
    "재즈 나오는 영화",
    "요리 소재 영화",
    "여행 가고 싶어지는 영화",
    "혼자 보기 좋은 잔잔한 영화",
    "연인이랑 보기 좋은 영화",
    "어린이날 아이랑 볼 영화",
    "명절에 온 가족이 볼 영화",
    "반전이 충격적인 영화",
    "범죄 스릴러 명작",
    "느와르 분위기 영화",
    "청춘 성장 영화",
    "첫사랑 생각나는 영화",
    "이별 후에 보면 좋은 영화",
    "동기부여 되는 영화",
    "스포츠 감동 실화 영화",
    "전쟁 영화 명작 추천",
    "역사 배경 한국 영화",
    "일제강점기 배경 영화",
    "조선시대 사극 영화",
    "정치 스릴러 영화",
    "언론 소재 영화",
    "의사 병원 배경 영화",
    "변호사 주인공 영화",
    "형사물 추천해줘",
    "스파이 첩보 영화",
    "카체이스 액션 영화",
    "재난 영화 추천",
    "바다 배경 영화",
    "산악 등반 영화",
    "비행기 소재 영화",
    "우정이 주제인 영화",
    "동물 나오는 힐링 영화",
    "강아지 나오는 영화",
    "고양이 나오는 영화",
    "로봇 AI 소재 영화",
    "디스토피아 세계관 영화",
    "밀실 탈출 스릴러",
    "심리전 두뇌 싸움 영화",
    "사기꾼 케이퍼 무비",
    "은행 강도 영화",
    "복수극 영화 추천",
    "잔잔한 일본 영화",
    "프랑스 감성 영화",
    "유럽 배경 로맨스",
    "뉴욕 배경 영화",
    "크리스마스 분위기 영화",
    "여름에 보기 좋은 영화",
    "가을 감성 영화",
    "겨울 배경 영화",
    "80년대 레트로 감성 영화",
    "2000년대 초반 한국 영화",
    "최근에 나온 인기 영화",
    "평점 높은 명작 추천",
    "저평가된 숨은 명작",
    "킬링타임용 액션 영화",
    "생각할 거리를 주는 영화",
    "철학적인 SF 영화",
    "꿈 소재 영화",
    "기억상실 소재 영화",
    "평행세계 멀티버스 영화",
    "뮤지컬 영화 추천",
    "춤 나오는 영화",
    "밴드 음악 영화",
    "화가 예술가 영화",
    "작가 소설가 주인공 영화",
    "천재 수학자 영화",
    "우울할 때 기분 좋아지는 영화",
    "스트레스 풀리는 통쾌한 영화",
    "몰입감 최고인 영화",
    "한 번에 정주행할 영화",
    "친구들이랑 왁자지껄 볼 영화",
    "부모님이랑 볼만한 영화",
    "10대가 공감할 영화",
    "직장인 공감 영화",
    "요즘 화제인 영화 뭐 있어",
    "인생 영화 추천해줘",
]

# 영화 의도가 없거나 불분명 — picks는 빈 배열이어야 한다.
NO_PICK_EXAMPLES = [
    ("안녕", "안녕하세요! 어떤 분위기의 영화를 찾으세요? 장르나 배우를 알려주시면 골라드릴게요."),
    ("안녕하세요", "반가워요! 오늘은 어떤 영화가 보고 싶으신가요?"),
    ("hi", "안녕하세요! 찾으시는 영화 장르나 분위기를 알려주세요."),
    ("뭐해", "저는 영화 추천을 도와드리는 Mova예요. 어떤 영화를 찾으시나요?"),
    ("고마워", "천만에요! 또 보고 싶은 영화가 생기면 언제든 물어보세요."),
    ("ㅋㅋㅋ", "재밌으셨다니 다행이에요! 다른 영화도 추천해드릴까요?"),
    (
        "오늘 날씨 어때",
        "날씨는 잘 모르지만, 오늘 기분에 맞는 영화는 골라드릴 수 있어요! 어떤 분위기를 원하세요?",
    ),
    ("심심해", "심심할 땐 영화죠! 액션, 코미디, 스릴러 중 어떤 게 끌리세요?"),
    ("추천", "어떤 장르나 분위기의 영화를 원하시는지 조금만 더 알려주시면 딱 맞게 골라드릴게요."),
    ("아무거나", "취향을 조금만 알려주세요! 최근에 재밌게 본 영화나 좋아하는 배우가 있나요?"),
]


async def main() -> None:
    from core.matrix.grid_oracle_database_manager import get_mova_session_factory
    from mova.adapter.outbound.llm.chat_prompt import ChatPromptBuilder
    from mova.adapter.outbound.llm.chat_reply import ChatReplyService
    from mova.adapter.outbound.llm.gemini_client import gemini_reply
    from mova.adapter.outbound.llm.intent_extraction import IntentExtractionService
    from mova.adapter.outbound.pg.market_chat_pg_repository import ChatPgRepository
    from mova.domain.value_objects.mood_expansion import expand_mood_keywords

    intent_svc = IntentExtractionService()
    builder = ChatPromptBuilder()
    reply_svc = ChatReplyService()
    factory = get_mova_session_factory()

    examples: list[dict] = []
    skipped: list[tuple[str, str]] = []

    for i, msg in enumerate(MOVIE_QUERIES):
        # 결정론적 추출만 사용 — Gemini 쿼터는 completion 생성에만 쓴다.
        intent = intent_svc._fallback_raw(msg)
        must = intent["search_filters"].get("must") or {}
        similar = intent["search_filters"].get("similar_to") or {}
        actor_names = [*must.get("actors", []), *similar.get("actors", [])]
        keywords = expand_mood_keywords(intent["keywords"])[:12]

        async with factory() as session:
            repo = ChatPgRepository(session=session)
            catalog = await repo.search_tag_catalog(
                keywords,
                limit=16,
                actor_names=actor_names,
                countries=must.get("countries") or [],
                year_min=intent["search_filters"].get("year_min"),
                year_max=intent["search_filters"].get("year_max"),
            )
        if not catalog:
            skipped.append((msg, "catalog empty"))
            continue

        catalog_ids = set()
        for c in catalog:
            try:
                catalog_ids.add(int(c.id))
            except (TypeError, ValueError):
                pass

        prompt = builder.build_prompt(
            [],
            msg,
            refined_query=intent["refined_query"] or msg,
            keywords=intent["keywords"],
            intent_type=intent["intent_type"],
            search_filters=intent["search_filters"],
            past_intents=[],
            tag_catalog=catalog,
            user_nickname=None,
            preferred_genres=[],
        )

        try:
            raw = gemini_reply(prompt, None)
        except Exception as e:  # noqa: BLE001 — 쿼터/일시 오류는 스킵하고 계속
            skipped.append((msg, f"gemini error: {e}"))
            time.sleep(SLEEP_SECONDS)
            continue

        data = reply_svc._extract_json(raw)
        if not data or not isinstance(data.get("picks"), list):
            skipped.append((msg, "no json"))
            time.sleep(SLEEP_SECONDS)
            continue

        valid_picks = []
        for p in data["picks"]:
            if not isinstance(p, dict):
                continue
            try:
                mid = int(p.get("movie_id"))
            except (TypeError, ValueError):
                continue
            if mid not in catalog_ids:
                continue  # 그라운딩 위반 pick 제외
            valid_picks.append(
                {
                    "movie_id": mid,
                    "title": str(p.get("title", "")).strip(),
                    "hook": str(p.get("hook", "")).strip()[:80],
                }
            )
        if not valid_picks:
            skipped.append((msg, "no grounded picks"))
            time.sleep(SLEEP_SECONDS)
            continue

        completion = json.dumps(
            {"intro": str(data.get("intro", "")).strip(), "picks": valid_picks[:3]},
            ensure_ascii=False,
        )
        examples.append({"prompt": prompt, "completion": completion})
        print(f"[{i + 1}/{len(MOVIE_QUERIES)}] ok picks={len(valid_picks[:3])} | {msg}", flush=True)
        time.sleep(SLEEP_SECONDS)

    # 영화 의도 없음 → 빈 picks 예시 (교사 호출 불필요, 직접 작성)
    for msg, intro in NO_PICK_EXAMPLES:
        prompt = builder.build_prompt(
            [],
            msg,
            refined_query=msg,
            keywords=[],
            intent_type="mood",
            search_filters={},
            past_intents=[],
            tag_catalog=[],
            user_nickname=None,
            preferred_genres=[],
        )
        completion = json.dumps({"intro": intro, "picks": []}, ensure_ascii=False)
        examples.append({"prompt": prompt, "completion": completion})

    random.shuffle(examples)
    with OUT.open("w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    print(f"\nDONE: {len(examples)} examples -> {OUT}")
    print(f"skipped {len(skipped)}:")
    for msg, why in skipped:
        print(f"  - {msg}: {why}")


if __name__ == "__main__":
    asyncio.run(main())
