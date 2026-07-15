"""mova 채팅 기록(chat+picks)을 QLoRA 학습용 (prompt, completion) JSONL로 추출한다.

picks가 있는 대화만 학습 예시로 쓴다 — chat 테이블엔 실제 답변 텍스트(intro)가
저장되지 않고 picks만 영속화되므로, intro는 합성한다. 프로덕션과 동일한
ChatPromptBuilder + HubRagInteractor로 프롬프트를 재구성해, 학습·서빙 프롬프트가
어긋나지 않게 한다. user_id가 있으면 그 사용자의 과거 대화(현재 chat 이전 것만)를
past_intents로 포함해, 반복 방문자의 취향이 프롬프트에 누적 반영되도록 한다.

Usage (suvisdev 폴더에서):
  python scripts/export_chat_training_dataset.py [--out PATH]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
_APPS = _BACKEND / "apps"
for _p in (_BACKEND, _APPS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

_DEFAULT_OUT = _APPS / "mova" / "_docs" / "chat_training_dataset.jsonl"


def _synthesize_intro(picks: list[dict]) -> str:
    titles = ", ".join(p["title_snapshot"] for p in picks[:3])
    return f"취향에 맞는 작품 {len(picks)}편을 골라봤어요: {titles}"


async def main(out_path: Path) -> None:
    from sqlalchemy import text

    from core.matrix.grid_oracle_database_manager import get_mova_session_factory, reload_env
    from mova.adapter.inbound.api.schemas.studio_search_schema import MovaSearchItemSchema
    from mova.adapter.outbound.llm.chat_prompt import ChatPromptBuilder
    from mova.adapter.outbound.pg.market_chat_pg_repository import ChatPgRepository
    from ontology.adapter.outbound.llm.ollama_embedding_adapter import OllamaEmbeddingAdapter
    from ontology.adapter.outbound.repositories.hub_knowledge_repository import (
        HubKnowledgeRepository,
    )
    from ontology.app.use_cases.hub_rag_interactor import HubRagInteractor

    reload_env()
    factory = get_mova_session_factory()
    prompt_builder = ChatPromptBuilder()

    examples: list[dict] = []
    async with factory() as session:
        repo = ChatPgRepository(session=session)
        hub_rag = HubRagInteractor(
            repository=HubKnowledgeRepository(session=session), embedding=OllamaEmbeddingAdapter()
        )

        rows = (
            (
                await session.execute(
                    text(
                        """
                        SELECT c.id, c.user_id, c.raw_message, c.refined_query, c.keywords,
                               c.intent_type, c.search_filters
                        FROM chat c
                        WHERE EXISTS (SELECT 1 FROM picks p WHERE p.chat_id = c.id)
                        ORDER BY c.id
                        """
                    )
                )
            )
            .mappings()
            .all()
        )

        for row in rows:
            picks_rows = (
                (
                    await session.execute(
                        text(
                            "SELECT title_snapshot, hook FROM picks "
                            "WHERE chat_id = :cid ORDER BY pick_rank"
                        ),
                        {"cid": row["id"]},
                    )
                )
                .mappings()
                .all()
            )
            picks = [dict(p) for p in picks_rows]
            if not picks:
                continue

            user_nickname: str | None = None
            preferred_genres: list[str] = []
            past_intents: list = []
            if row["user_id"]:
                pref_row = (
                    (
                        await session.execute(
                            text("SELECT nickname, preferred_genres FROM users WHERE id = :uid"),
                            {"uid": row["user_id"]},
                        )
                    )
                    .mappings()
                    .first()
                )
                if pref_row:
                    user_nickname = pref_row["nickname"]
                    preferred_genres = list(pref_row["preferred_genres"] or [])
                # 미래 데이터 유출 방지 — 이 chat보다 먼저 있었던 것만 과거 취향으로 사용.
                recent = await repo.get_recent_intents_by_user(row["user_id"], limit=3)
                past_intents = [pi for pi in recent if pi.id < row["id"]]

            hits = await hub_rag.search_movies(row["refined_query"] or row["raw_message"], k=8)
            tag_catalog = [
                MovaSearchItemSchema(
                    id=h.source_ref, title=h.title, year="", rating=0.0, poster="",
                    match_type="semantic",
                )
                for h in hits
            ]

            prompt = prompt_builder.build_prompt(
                [],
                row["raw_message"],
                refined_query=row["refined_query"],
                keywords=list(row["keywords"] or []),
                intent_type=row["intent_type"],
                search_filters=dict(row["search_filters"] or {}),
                past_intents=past_intents,
                tag_catalog=tag_catalog,
                user_nickname=user_nickname,
                preferred_genres=preferred_genres,
            )
            target = {
                "intro": _synthesize_intro(picks),
                "picks": [
                    {"title": p["title_snapshot"], "hook": p["hook"] or ""} for p in picks
                ],
            }
            examples.append(
                {
                    "chat_id": row["id"],
                    "user_id": row["user_id"],
                    "prompt": prompt,
                    "completion": json.dumps(target, ensure_ascii=False),
                }
            )
            print(
                f"[export] chat_id={row['id']} user_id={row['user_id']} picks={len(picks)}",
                flush=True,
            )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    print(f"[export] 완료: {len(examples)}건 -> {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=_DEFAULT_OUT)
    args = parser.parse_args()
    asyncio.run(main(args.out))
