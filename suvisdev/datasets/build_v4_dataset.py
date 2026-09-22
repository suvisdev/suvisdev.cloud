"""v4 학습 데이터 — 새 카탈로그 형식(장르·줄거리)으로 전량 재구성 + 배우 질의 교정.

배경(2026-09-22): 서빙 프롬프트가 카탈로그 줄에 장르·한 줄 줄거리를 싣도록
바뀌었다(v3 평가 패배 25건 중 카탈로그 사유 16건). 기존 v3 데이터 619행은
옛 형식(제목·연도·태그만)이라 그대로 학습하면 학습·서빙 프롬프트가 어긋난다.
또 v3를 서빙해 보니 배우 질의("송강호 나오는 영화")에서 카탈로그에 그 배우
작품 8편이 있는데도 picks를 비웠다 — v3_honest(다른 배우 카탈로그 → 0편)가
과잉 일반화된 것이라 "있으면 반드시 고른다" 예시를 실제 서빙 카탈로그 형태로
보강한다.

  ① rebuild  v3 행의 카탈로그 줄을 DB 값으로 새 형식으로 치환 (교사 호출 없음,
             completion은 movie_id 기반이라 그대로 유효)
  ② teacher  gen_teacher_dataset.MOVIE_QUERIES를 실제 파이프라인으로 다시 생성
             (새 형식 프롬프트를 본 교사 응답 — 줄거리를 근거로 쓴 intro/hook)
  ③ actor    DB 상위 배우 × 발화 2종 → 실제 search_tag_catalog(actor+keyword 혼합)
             카탈로그 → 교사. picks가 전부 그 배우 작품이고 1편 이상일 때만 채택

파드 안에서 실행한다(DB·GEMINI_API_KEY 필요):
  kubectl cp datasets/build_v4_dataset.py <pod>:/suvisdev/datasets/
  kubectl cp datasets/chat_teacher_dataset_v3.jsonl <pod>:/suvisdev/datasets/
  kubectl exec <pod> -- sh -c "cd /suvisdev && PYTHONPATH=/suvisdev:/suvisdev/apps \
      python datasets/build_v4_dataset.py [--limit N] [--skip-teacher]"
출력: datasets/chat_teacher_dataset_v4.jsonl (+ 중간 산출 v4_base / v4_new)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
import sys
import time
from pathlib import Path

for p in ("/suvisdev/apps", "/suvisdev", str(Path(__file__).resolve().parent)):
    sys.path.insert(0, p)

_D = Path(__file__).resolve().parent
_V3 = _D / "chat_teacher_dataset_v3.jsonl"
_BASE = _D / "chat_teacher_dataset_v4_base.jsonl"
_NEW = _D / "chat_teacher_dataset_v4_new.jsonl"
_OUT = _D / "chat_teacher_dataset_v4.jsonl"

SLEEP_SECONDS = 4.5  # Gemini 무료 티어 15req/min
_ACTOR_TOP_N = 30
_ACTOR_UTTER = ["{a} 나오는 영화", "{a} 영화 추천해줘"]

# 옛 카탈로그 줄: "- movie_id=5270 캔터빌의 유령 (2025) [태그]"
_OLD_LINE_RE = re.compile(r"^- movie_id=(\d+) (.+?) \((\d{4}|연도 미상)\) \[([^\]]+)\]$")
_HANJA_RE = re.compile(r"[一-鿿]")


# ── ① rebuild ───────────────────────────────────────────────────────────────


def _catalog_ids(prompt: str) -> list[int]:
    return [int(m.group(1)) for line in prompt.split("\n") if (m := _OLD_LINE_RE.match(line))]


def _rebuild_line(line: str, genres: dict[int, list[str]], summary: dict[int, str]) -> str:
    m = _OLD_LINE_RE.match(line)
    if not m:
        return line
    mid, title, year, kind = int(m.group(1)), m.group(2), m.group(3), m.group(4)
    parts = [f"- movie_id={mid} {title} ({year})"]
    if genres.get(mid):
        parts.append(f"[{', '.join(genres[mid])}]")
    parts.append(f"[{kind}]")
    if summary.get(mid):
        parts.append(f"— 줄거리: {summary[mid]}")
    return " ".join(parts)


async def rebuild(factory, rows: list[dict]) -> list[dict]:
    from sqlalchemy import select

    from mova.adapter.outbound.orm.studio_movies_orm import MovaMovie
    from mova.adapter.outbound.pg.market_chat_pg_repository import ChatPgRepository, _shorten

    ids = sorted({mid for r in rows for mid in _catalog_ids(r["prompt"])})
    async with factory() as session:
        repo = ChatPgRepository(session=session)
        genres = await repo._genres_by_movie_ids(ids)
        syn = await session.execute(
            select(MovaMovie.id, MovaMovie.synopsis).where(MovaMovie.id.in_(ids))
        )
        summary = {mid: _shorten(s) for mid, s in syn.all()}
    print(
        f"[rebuild] 카탈로그 영화 {len(ids)}편 — 장르 {len(genres)} · 줄거리 {sum(1 for v in summary.values() if v)}"
    )

    out: list[dict] = []
    for r in rows:
        prompt = "\n".join(_rebuild_line(ln, genres, summary) for ln in r["prompt"].split("\n"))
        out.append({**r, "prompt": prompt, "src": "v4_rebuild"})
    return out


# ── ②③ teacher ──────────────────────────────────────────────────────────────


def _grounded_picks(data: dict, catalog_ids: set[int]) -> list[dict]:
    picks = []
    for p in data.get("picks") or []:
        if not isinstance(p, dict):
            continue
        try:
            mid = int(p.get("movie_id"))
        except (TypeError, ValueError):
            continue
        if mid in catalog_ids:
            picks.append(
                {
                    "movie_id": mid,
                    "title": str(p.get("title", "")).strip(),
                    "hook": str(p.get("hook", "")).strip()[:80],
                }
            )
    return picks[:3]


async def _top_actors(factory) -> list[str]:
    from sqlalchemy import func, select

    from mova.adapter.outbound.orm.studio_actors_orm import MovaActor
    from mova.adapter.outbound.orm.studio_characters_orm import MovaCharacter

    async with factory() as session:
        rows = await session.execute(
            select(MovaActor.name, func.count(MovaCharacter.movie_id).label("n"))
            .join(MovaCharacter, MovaCharacter.actor_id == MovaActor.id)
            .where(MovaActor.role_type == "actor", MovaActor.name.op("~")(r"^[가-힣]{2,5}$"))
            .group_by(MovaActor.name)
            .order_by(func.count(MovaCharacter.movie_id).desc())
            .limit(_ACTOR_TOP_N)
        )
        return [r[0] for r in rows]


async def teacher(factory, *, limit: int, skip_base_queries: bool) -> list[dict]:
    from gen_teacher_dataset import MOVIE_QUERIES

    from mova.adapter.outbound.llm.chat_prompt import ChatPromptBuilder
    from mova.adapter.outbound.llm.chat_reply import ChatReplyService
    from mova.adapter.outbound.llm.gemini_client import gemini_reply
    from mova.adapter.outbound.llm.intent_extraction import IntentExtractionService
    from mova.adapter.outbound.pg.market_chat_pg_repository import ChatPgRepository
    from mova.domain.value_objects.mood_expansion import expand_mood_keywords

    intent_svc, builder, reply_svc = (
        IntentExtractionService(),
        ChatPromptBuilder(),
        ChatReplyService(),
    )

    jobs: list[tuple[str, str, str | None]] = []  # (message, aug, actor)
    if not skip_base_queries:
        jobs += [(q, "v4_teacher", None) for q in MOVIE_QUERIES]
    actors = await _top_actors(factory)
    print(f"[actor] 상위 배우 {len(actors)}명: {', '.join(actors[:10])} …")
    for a in actors:
        for u in _ACTOR_UTTER:
            jobs.append((u.format(a=a), "v4_actor", a))
    if limit:
        jobs = jobs[:limit]

    examples, skipped, calls = [], [], 0
    for i, (msg, aug, actor) in enumerate(jobs):
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
            actor_movies = await repo._movie_ids_by_actors([actor]) if actor else set()
        if not catalog:
            skipped.append((msg, "catalog empty"))
            continue
        catalog_ids = {int(c.id) for c in catalog}
        if actor and not (catalog_ids & actor_movies):
            skipped.append((msg, "배우 작품이 카탈로그에 없음 — v3_honest 영역"))
            continue

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
        calls += 1
        data = reply_svc._extract_json(raw)
        picks = _grounded_picks(data, catalog_ids) if data else []
        why = None
        if not picks:
            why = "no grounded picks"
        elif actor and any(p["movie_id"] not in actor_movies for p in picks):
            why = "배우 작품 아닌 pick 포함"
        elif _HANJA_RE.search(raw):
            why = "한자 혼입"
        if why:
            skipped.append((msg, why))
        else:
            completion = json.dumps(
                {"intro": str(data.get("intro", "")).strip(), "picks": picks}, ensure_ascii=False
            )
            examples.append({"prompt": prompt, "completion": completion, "aug": aug, "src": "v4"})
            print(f"[{i + 1}/{len(jobs)}] ok {aug} picks={len(picks)} | {msg}", flush=True)
        time.sleep(SLEEP_SECONDS)

    print(f"\n[teacher] {len(examples)}행 채택 · 교사 {calls}회 · 버림 {len(skipped)}")
    for msg, why in skipped:
        print(f"  - {msg}: {why}")
    return examples


# ── main ────────────────────────────────────────────────────────────────────


def _write(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=0, help="교사 작업 상한(0=무제한)")
    ap.add_argument("--skip-teacher", action="store_true", help="① rebuild만 수행")
    ap.add_argument("--actors-only", action="store_true", help="③ 배우 보강만 교사 호출")
    args = ap.parse_args()

    from core.matrix.grid_oracle_database_manager import get_mova_session_factory

    factory = get_mova_session_factory()
    v3 = [json.loads(ln) for ln in _V3.open(encoding="utf-8") if ln.strip()]
    base = await rebuild(factory, v3)
    _write(_BASE, base)
    print(f"[rebuild] {len(base)}행 → {_BASE}")

    new: list[dict] = []
    if not args.skip_teacher:
        new = await teacher(factory, limit=args.limit, skip_base_queries=args.actors_only)
        _write(_NEW, new)

    merged = base + new
    random.Random(4).shuffle(merged)
    _write(_OUT, merged)
    print(f"[v4] {len(merged)}행 (rebuild {len(base)} + new {len(new)}) → {_OUT}")


if __name__ == "__main__":
    asyncio.run(main())
