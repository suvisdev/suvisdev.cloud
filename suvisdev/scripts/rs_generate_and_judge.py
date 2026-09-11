"""RS 교사 루프 2단계 — 엑사온 N-후보 생성 → Gemini 루브릭 심판 → 데이터셋 v2.

기존 gen_teacher_dataset.py(교사가 직접 작성)와 달리, **학생(EXAONE LoRA)이
후보를 만들고 교사(Gemini)는 고르기만** 한다(rejection sampling) — 학생 능력
범위 안의 좋은 출력으로 학습하므로 문체 붕괴 없이 수렴이 좋다. 후보가 전부
탈락하면 교사 작성으로 폴백(source=teacher)해 커버리지를 지킨다.

전제(데스크톱): lora-server(systemd, :8200) 기동 중 — 내부 llama-server
(:8201, OpenAI 호환)를 직접 호출해 temperature 샘플링한다(공개 /generate는
greedy 고정). 프로덕션 서빙 경로는 건드리지 않는다.

운영 원칙(2026-09-03 배치 큐): 이 스크립트는 **데이터셋만** 만든다. 학습은
유의미 증분이 쌓였을 때 train_mova_lora.py → export_mova_gguf.py → /reload
순서로 한 번에(상세: _docs/RS_TEACHER_LOOP.md).

Usage (suvisdev/에서):
  python scripts/rs_generate_and_judge.py --limit 5          # 소량 검증
  python scripts/rs_generate_and_judge.py                    # 전체(재개 지원)
  python scripts/rs_generate_and_judge.py --queries datasets/rs_queries.jsonl
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

import httpx

_BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(_BACKEND), str(_BACKEND / "apps")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_LLAMA_URL = "http://127.0.0.1:8201/v1/chat/completions"
_TEMPERATURES = (0.0, 0.5, 0.8, 1.1)  # greedy 포함 4후보
_MAX_TOKENS = 320
_JUDGE_SLEEP_SECONDS = 4.5  # Gemini 무료 티어 15req/min
_JUDGE_THRESHOLD = 7  # 10점 만점 — 미만이면 교사 작성 폴백

_OUT_DATASET = _BACKEND / "datasets" / "chat_teacher_dataset_v2.jsonl"
_OUT_AUDIT = _BACKEND / "datasets" / "rs_audit.jsonl"

_JUDGE_PROMPT = """당신은 영화 추천 챗봇 응답의 심사위원입니다. 사용자 질의와
후보 응답들을 보고 **가장 좋은 응답 하나**를 고르세요.

채점 기준(중요한 순):
1. 그라운딩 — 질의 조건(장르·분위기·배우·연도)에 실제로 맞는 픽인가
2. intro 말투 — 존댓말, 1~2문장, 과장·확신 남발 금지, 자연스러운 한국어
3. hook — 각 픽의 한 줄 어필이 구체적이고 스포일러 없이 매력적인가
4. 정직성 — 조건에 안 맞는 걸 맞는 척하지 않는가

[사용자 질의]
{query}

[카탈로그 발췌 — 픽은 전부 이 안의 작품]
{catalog}

[후보 응답들]
{candidates}

JSON 한 줄만 출력:
{{"best": <가장 좋은 후보 번호(1부터), 전부 나쁘면 0>, "score": <best의 10점 만점 점수>, "reason": "<한 문장>"}}
"""


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queries", default=None, help="질의 JSONL(rs_mine_queries 출력)")
    parser.add_argument("--limit", type=int, default=None, help="앞 N개 질의만")
    parser.add_argument("--no-teacher-fallback", action="store_true")
    return parser.parse_args(argv)


def _load_queries(path: str | None) -> list[str]:
    queries: list[str] = []
    if path:
        with Path(path).open(encoding="utf-8") as f:
            queries.extend(json.loads(line)["query"] for line in f if line.strip())
    # 정적 풀 병합 — 실사용 질의가 적어도 커버리지 확보
    sys.path.insert(0, str(_BACKEND / "datasets"))
    from gen_teacher_dataset import MOVIE_QUERIES  # noqa: E402

    seen = set(queries)
    queries.extend(q for q in MOVIE_QUERIES if q not in seen)
    return queries


def _done_queries() -> set[str]:
    """재개 지원 — audit 로그에 기록된 질의는 건너뛴다."""
    if not _OUT_AUDIT.exists():
        return set()
    done = set()
    with _OUT_AUDIT.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                done.add(json.loads(line)["query"])
    return done


def _sample_candidates(prompt: str) -> list[str]:
    """내부 llama-server에서 온도별 후보 생성. cache_prompt로 프리픽스 재사용."""
    outputs: list[str] = []
    for temperature in _TEMPERATURES:
        try:
            r = httpx.post(
                _LLAMA_URL,
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": _MAX_TOKENS,
                    "temperature": temperature,
                    "cache_prompt": True,
                },
                timeout=180.0,
            )
            r.raise_for_status()
            outputs.append(r.json()["choices"][0]["message"]["content"])
        except httpx.HTTPError as e:
            print(f"  [gen] temperature={temperature} 실패: {e}")
    return outputs


def _validate_candidate(raw: str, catalog_ids: set[int], reply_svc) -> dict | None:
    """JSON 파싱 + 그라운딩 하드 필터 — 통과 못 하면 심판에 못 올라간다."""
    data = reply_svc._extract_json(raw)
    if not data or not isinstance(data.get("picks"), list):
        return None
    picks = []
    for p in data["picks"]:
        if not isinstance(p, dict):
            return None
        try:
            mid = int(p.get("movie_id"))
        except (TypeError, ValueError):
            return None
        if mid not in catalog_ids:
            return None  # 그라운딩 위반은 후보 자체를 탈락
        picks.append(
            {
                "movie_id": mid,
                "title": str(p.get("title", "")).strip(),
                "hook": str(p.get("hook", "")).strip()[:80],
            }
        )
    intro = str(data.get("intro", "")).strip()
    if not intro or not picks:
        return None
    return {"intro": intro, "picks": picks[:3]}


def _judge(
    query: str, catalog_text: str, candidates: list[dict], gemini_reply
) -> tuple[int, int, str]:
    """(best_index(0=전부 탈락), score, reason)."""
    numbered = "\n\n".join(
        f"### 후보 {i + 1}\n{json.dumps(c, ensure_ascii=False)}" for i, c in enumerate(candidates)
    )
    raw = gemini_reply(
        _JUDGE_PROMPT.format(query=query, catalog=catalog_text, candidates=numbered), None
    )
    try:
        start, end = raw.find("{"), raw.rfind("}")
        data = json.loads(raw[start : end + 1])
        best = int(data.get("best", 0))
        score = int(data.get("score", 0))
        reason = str(data.get("reason", ""))
    except (ValueError, TypeError):
        return 0, 0, f"judge parse 실패: {raw[:80]}"
    if not (1 <= best <= len(candidates)):
        return 0, score, reason
    return best, score, reason


async def _run(args: argparse.Namespace) -> None:
    from core.matrix.grid_oracle_database_manager import get_mova_session_factory
    from core.matrix.vauly_keymaker_secret_manager import get_keymaker

    get_keymaker()  # .env 로드 — DB·Gemini 키

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

    queries = _load_queries(args.queries)
    done = _done_queries()
    queries = [q for q in queries if q not in done]
    if args.limit:
        queries = queries[: args.limit]
    print(f"[rs] 대상 {len(queries)}건 (기존 처리 {len(done)}건 스킵)")

    accepted = teacher_fallbacks = skipped = 0
    for i, query in enumerate(queries):
        intent = intent_svc._fallback_raw(query)
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
            skipped += 1
            _append(_OUT_AUDIT, {"query": query, "source": "skip", "reason": "catalog empty"})
            continue
        catalog_ids = {int(c.id) for c in catalog if str(c.id).isdigit()}
        catalog_text = "\n".join(f"- {c.id}: {c.title} ({c.year})" for c in catalog)

        prompt = builder.build_prompt(
            [],
            query,
            refined_query=intent["refined_query"] or query,
            keywords=intent["keywords"],
            intent_type=intent["intent_type"],
            search_filters=intent["search_filters"],
            past_intents=[],
            tag_catalog=catalog,
            user_nickname=None,
            preferred_genres=[],
        )

        raw_candidates = _sample_candidates(prompt)
        valid, seen_keys = [], set()
        for raw in raw_candidates:
            c = _validate_candidate(raw, catalog_ids, reply_svc)
            if c is None:
                continue
            key = (c["intro"], tuple(p["movie_id"] for p in c["picks"]))
            if key not in seen_keys:  # 온도만 다르고 동일한 출력은 1개로
                seen_keys.add(key)
                valid.append(c)

        best_idx, score, reason = (0, 0, "유효 후보 없음")
        if valid:
            best_idx, score, reason = _judge(query, catalog_text, valid, gemini_reply)
            time.sleep(_JUDGE_SLEEP_SECONDS)

        if best_idx >= 1 and score >= _JUDGE_THRESHOLD:
            completion = json.dumps(valid[best_idx - 1], ensure_ascii=False)
            _append(_OUT_DATASET, {"prompt": prompt, "completion": completion})
            _append(
                _OUT_AUDIT,
                {
                    "query": query,
                    "source": "student",
                    "score": score,
                    "reason": reason,
                    "candidates": len(valid),
                },
            )
            accepted += 1
            print(f"[{i + 1}/{len(queries)}] student ok score={score} | {query}", flush=True)
            continue

        if args.no_teacher_fallback:
            skipped += 1
            _append(_OUT_AUDIT, {"query": query, "source": "skip", "reason": reason})
            continue

        # 교사 작성 폴백 — gen_teacher_dataset과 동일 검증
        try:
            raw = gemini_reply(prompt, None)
        except Exception as e:  # noqa: BLE001 — 쿼터/일시 오류는 스킵하고 계속
            skipped += 1
            _append(_OUT_AUDIT, {"query": query, "source": "skip", "reason": f"gemini: {e}"})
            time.sleep(_JUDGE_SLEEP_SECONDS)
            continue
        teacher = _validate_candidate(raw, catalog_ids, reply_svc)
        time.sleep(_JUDGE_SLEEP_SECONDS)
        if teacher is None:
            skipped += 1
            _append(_OUT_AUDIT, {"query": query, "source": "skip", "reason": "teacher invalid"})
            continue
        _append(
            _OUT_DATASET, {"prompt": prompt, "completion": json.dumps(teacher, ensure_ascii=False)}
        )
        _append(_OUT_AUDIT, {"query": query, "source": "teacher", "score": score, "reason": reason})
        teacher_fallbacks += 1
        print(f"[{i + 1}/{len(queries)}] teacher 폴백 | {query}", flush=True)

    print(
        f"[rs] 완료 student={accepted} teacher={teacher_fallbacks} skip={skipped} "
        f"→ {_OUT_DATASET}"
    )


def _append(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    asyncio.run(_run(_parse_args()))
