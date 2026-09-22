"""v5 학습 데이터 — "후보가 있으면 고른다" 재균형 + 연도·장르 질의 긍정 예시 보강.
배경(2026-09-22 밤): v4를 서빙하니 배우 질의는 살아났지만 `2000년대 초반 한국 영화`
(후보 6편)·`법정 드라마 영화`(후보 16편)가 0편으로 회귀했다. v4 895행 중 0편 행이
192행(21%)이고, 그중 117행은 카탈로그에 3편 이상 있는데도 0편 — 특히
`v3_honest_genre` 48행은 "12편이 있지만 「액션」에 맞는 게 없다"를 가르친다. 모델은
장르 불일치를 정확히 판단할 수 없어 이 규칙을 "확신이 없으면 0편"으로 과잉 일반화한다
(v3 배우 → v4 연도·장르로 자리만 옮겨 다님).
  ① 재균형  v4에서 `v3_honest_genre` 전량 제거, `v3_honest`(배우 불일치)는 12행만 유지.
            빈 카탈로그·인사(mt_smalltalk)의 0편 행은 정당하므로 그대로 둔다.
  ② teacher  연도 범위·장르/키워드 질의를 실제 서빙 파이프라인으로 돌려 Gemini 교사
            응답을 받는다. 후보 조립은 인터랙터와 같은 순서 — RAG(bge-m3, k=8) → 연도
            필터 → 태그 검색 합집합(v4 빌더는 태그 검색만 써서 연도 질의가 후보 0건이었다).
            근거 있는 pick 1편 이상일 때만 채택. Gemini 503/429는 백오프 재시도.
호스트 Ollama(bge-m3)가 떠 있어야 한다(`curl :11434/api/tags`).
노트북 호스트에서 이미지 컨테이너로 실행(DB localhost:5432·GEMINI_API_KEY는 .env):
  docker run --rm --network host -v "$PWD":/src:ro -v "$PWD/datasets":/src/datasets \
    -w /src --env-file .env -e PYTHONPATH=/src:/src/apps suvisdev-app:latest \
    python datasets/build_v5_dataset.py [--limit N] [--skip-teacher]
출력: datasets/chat_teacher_dataset_v5.jsonl (+ v5_new 중간 산출)
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import random
import sys
import time
from pathlib import Path

for p in ("/suvisdev/apps", "/suvisdev", str(Path(__file__).resolve().parent)):
    sys.path.insert(0, p)

from build_v4_dataset import _HANJA_RE, _grounded_picks  # noqa: E402

from mova.adapter.inbound.api.schemas.studio_search_schema import (  # noqa: E402
    MovaSearchItemSchema,
)

_D = Path(__file__).resolve().parent
_V4 = _D / "chat_teacher_dataset_v4.jsonl"
_NEW = _D / "chat_teacher_dataset_v5_new.jsonl"
_OUT = _D / "chat_teacher_dataset_v5.jsonl"
_CACHE = _D / ".v5_cache.json"
SLEEP_SECONDS = 4.5  # Gemini 무료 티어 15req/min
_HONEST_KEEP = 12

# 서빙 회귀가 난 두 계열 + 그 이웃. 기존 MOVIE_QUERIES와 겹치지 않는 표현으로.
V5_QUERIES = [
    # 연도 범위
    "2000년대 초반 한국 영화",
    "2010년대 한국 스릴러",
    "90년대 할리우드 액션 영화",
    "2020년 이후 나온 한국 영화",
    "2000년대 로맨스 영화 추천",
    "80년대 명작 영화",
    "2015년 이후 애니메이션",
    "최근 5년 안에 나온 공포 영화",
    "2000년대 초반 할리우드 로맨틱 코미디",
    "2010년 이전 한국 코미디 영화",
    "2020년대 SF 영화",
    "2000년대 한국 범죄 영화",
    # 장르·키워드
    "법정에서 벌어지는 영화",
    "재판 소재 영화 추천",
    "액션 영화 추천해줘",
    "미스터리 영화 추천",
    "판타지 영화 볼만한 거",
    "드라마 장르 명작 추천",
    "모험 영화 추천해줘",
    "탐정 추리물 영화",
    "범죄 조직 느와르 영화",
    "복수극 영화 추천",
    "심리 스릴러 영화",
    "감옥 배경 영화",
    "학교 배경 청춘 영화",
    "군대 소재 영화",
    "의학 드라마 영화",
    "언론 저널리즘 영화",
    "변호사가 주인공인 한국 영화",
    "검사 나오는 영화",
]


def rebalance(rows: list[dict], rng: random.Random) -> tuple[list[dict], dict[str, int]]:
    honest = [r for r in rows if r.get("aug") == "v3_honest"]
    keep_honest = set(id(r) for r in rng.sample(honest, min(_HONEST_KEEP, len(honest))))
    out, dropped = [], {"v3_honest_genre": 0, "v3_honest": 0}
    for r in rows:
        if r.get("aug") == "v3_honest_genre":
            dropped["v3_honest_genre"] += 1
            continue
        if r.get("aug") == "v3_honest" and id(r) not in keep_honest:
            dropped["v3_honest"] += 1
            continue
        out.append(r)
    return out, dropped


def _claude_reply(prompt: str) -> str:
    import anthropic

    msg = anthropic.Anthropic().messages.create(
        model="claude-haiku-4-5", max_tokens=1024, messages=[{"role": "user", "content": prompt}]
    )
    return "".join(b.text for b in msg.content if b.type == "text")


async def teacher(factory, *, limit: int, backend: str = "gemini") -> list[dict]:
    from mova.adapter.outbound.llm.chat_prompt import ChatPromptBuilder
    from mova.adapter.outbound.llm.chat_reply import ChatReplyService
    from mova.adapter.outbound.llm.gemini_client import gemini_reply
    from mova.adapter.outbound.llm.intent_extraction import IntentExtractionService
    from mova.adapter.outbound.pg.market_chat_pg_repository import ChatPgRepository
    from mova.domain.value_objects.franchise_expansion import expand_franchise_titles
    from mova.domain.value_objects.mood_expansion import expand_mood_keywords
    from ontology.adapter.outbound.llm.ollama_embedding_adapter import OllamaEmbeddingAdapter
    from ontology.adapter.outbound.repositories.hub_knowledge_repository import (
        HubKnowledgeRepository,
    )
    from ontology.app.use_cases.hub_rag_interactor import HubRagInteractor

    intent_svc, builder, reply_svc = (
        IntentExtractionService(),
        ChatPromptBuilder(),
        ChatReplyService(),
    )
    jobs = V5_QUERIES[:limit] if limit else V5_QUERIES
    cache: dict[str, str] = (
        json.loads(_CACHE.read_text(encoding="utf-8")) if _CACHE.exists() else {}
    )
    examples, skipped, calls = [], [], 0
    for i, msg in enumerate(jobs):
        intent = intent_svc._fallback_raw(msg)
        must = intent["search_filters"].get("must") or {}
        similar = intent["search_filters"].get("similar_to") or {}
        actor_names = [*must.get("actors", []), *similar.get("actors", [])]
        keywords = expand_mood_keywords(intent["keywords"])[:12]
        year_min = intent["search_filters"].get("year_min")
        year_max = intent["search_filters"].get("year_max")
        async with factory() as session:
            repo = ChatPgRepository(session=session)
            rag = HubRagInteractor(
                repository=HubKnowledgeRepository(session=session),
                embedding=OllamaEmbeddingAdapter(),
            )
            hits = await rag.search_movies(intent["refined_query"] or msg, k=8, trace_id="v5")
            catalog = [
                MovaSearchItemSchema(
                    id=h.source_ref,
                    title=h.title,
                    year="",
                    rating=0.0,
                    poster="",
                    match_type="semantic",
                )
                for h in hits
            ]
            if catalog and (year_min is not None or year_max is not None):
                ids = [int(c.id) for c in catalog if str(c.id).isdigit()]
                valid = await repo.filter_movie_ids_by_year(ids, year_min, year_max)
                catalog = [c for c in catalog if str(c.id).isdigit() and int(c.id) in valid]
            tag_items = await repo.search_tag_catalog(
                keywords if not catalog else intent["keywords"],
                limit=16,
                actor_names=actor_names,
                countries=must.get("countries") or [],
                year_min=year_min,
                year_max=year_max,
                title_terms=expand_franchise_titles(intent["keywords"]),
            )
        has_hard_filter = (
            bool(must.get("countries")) or year_min is not None or year_max is not None
        )
        real = [t for t in tag_items if t.match_type != "popular_fallback" or has_hard_filter]
        if real:
            if real[0].match_type in ("actor", "actor+keyword"):
                catalog = real[:16]
            else:
                head = real[:10]
                head_ids = {t.id for t in head}
                catalog = (head + [c for c in catalog if c.id not in head_ids])[:16]
        elif not catalog:
            catalog = tag_items[:16]  # 인터랙터 폴백(mood 확장 키워드 검색)과 동일
        if not catalog:
            skipped.append((msg, "catalog empty"))
            continue
        catalog_ids = {int(c.id) for c in catalog}
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
        # 캐시 키에 교사 모델을 섞는다 — Gemini 응답을 Claude 것으로 오인하지 않게
        key = hashlib.sha1((backend + "\n" + prompt).encode("utf-8")).hexdigest()
        raw = cache.get(key)
        called = raw is None
        if raw is None:
            for attempt in range(4):  # 503 UNAVAILABLE·429는 백오프 재시도(09-23 실측 대부분 503)
                try:
                    raw = (
                        _claude_reply(prompt) if backend == "claude" else gemini_reply(prompt, None)
                    )
                    break
                except Exception as e:  # noqa: BLE001
                    last = e
                    time.sleep(SLEEP_SECONDS * (2**attempt))
            if raw is None:
                skipped.append((msg, f"gemini error: {last}"))
                continue
            calls += 1
            cache[key] = raw
            _CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        data = reply_svc._extract_json(raw)
        picks = _grounded_picks(data, catalog_ids) if data else []
        if not picks:
            skipped.append((msg, f"no grounded picks (catalog {len(catalog)})"))
        elif _HANJA_RE.search(raw):
            skipped.append((msg, "한자 혼입"))
        else:
            completion = json.dumps(
                {"intro": str(data.get("intro", "")).strip(), "picks": picks}, ensure_ascii=False
            )
            examples.append(
                {
                    "prompt": prompt,
                    "completion": completion,
                    "aug": "orig",
                    "src": 20_000 + i,
                    "gen": f"v5_teacher_{backend}",
                }
            )
            print(
                f"[{i + 1}/{len(jobs)}] ok picks={len(picks)} catalog={len(catalog)} | {msg}",
                flush=True,
            )
        if called:
            time.sleep(SLEEP_SECONDS)
    print(f"\n[teacher] {len(examples)}행 채택 · 교사 {calls}회 · 버림 {len(skipped)}")
    for msg, why in skipped:
        print(f"  - {msg}: {why}")
    return examples


def _write(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--skip-teacher", action="store_true")
    ap.add_argument(
        "--teacher",
        choices=["gemini", "claude"],
        default="gemini",
        help="교사 모델. claude=Haiku 4.5(ANTHROPIC_API_KEY, 컨테이너에 `pip install anthropic`)",
    )
    args = ap.parse_args()

    v4 = [json.loads(ln) for ln in _V4.open(encoding="utf-8") if ln.strip()]
    base, dropped = rebalance(v4, random.Random(5))
    print(f"[rebalance] v4 {len(v4)}행 → {len(base)}행 (제거 {dropped})")

    new: list[dict] = []
    if not args.skip_teacher:
        from core.matrix.grid_oracle_database_manager import get_mova_session_factory

        new = await teacher(get_mova_session_factory(), limit=args.limit, backend=args.teacher)
        _write(_NEW, new)

    merged = base + new
    random.Random(5).shuffle(merged)
    _write(_OUT, merged)
    zero = sum(1 for r in merged if not json.loads(r["completion"])["picks"])
    print(f"[v5] {len(merged)}행 (base {len(base)} + new {len(new)}), 0편 행 {zero} → {_OUT}")


if __name__ == "__main__":
    asyncio.run(main())
