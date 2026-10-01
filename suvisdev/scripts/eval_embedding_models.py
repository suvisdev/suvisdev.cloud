"""RAG 임베딩 모델 후보 비교 하네스 — nomic vs 다국어 후보 (2026-09-11).

로컬 DB의 hub_knowledge(mova_movie) 문서를 코퍼스로, 장르 태그 멤버십을
정답(relevance)으로 삼아 Recall@8·MRR@8을 모델별로 잰다. 서빙은 노트북
Ollama지만 평가 가중치는 HF 동일 모델을 데스크톱 GPU로 직접 돌린다.

이기는 모델이 현행(nomic-embed-text, 768차원)과 다르면:
  ① 768차원 초과 모델은 EMBEDDING_DIM·Vector(768) 마이그레이션 필요
  ② 노트북 Ollama pull + OLLAMA_EMBED_MODEL 변경
  ③ scripts/ingest_hub_knowledge.py --reset 재임베딩 (백엔드 교체 시 필수)

Usage (suvisdev/에서, GPU 권장):
  python scripts/eval_embedding_models.py            # 기본 3종 비교
  python scripts/eval_embedding_models.py --models intfloat/multilingual-e5-base
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(_BACKEND), str(_BACKEND / "apps")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# (HF id, 쿼리 접두, 문서 접두, 풀링, trust_remote_code)
MODEL_SPECS: dict[str, dict] = {
    "nomic-ai/nomic-embed-text-v1.5": {
        "q_prefix": "search_query: ",
        "d_prefix": "search_document: ",
        "pooling": "mean",
        "trust": True,
        "note": "현행 서빙 모델(Ollama nomic-embed-text), 768차원",
    },
    "intfloat/multilingual-e5-base": {
        "q_prefix": "query: ",
        "d_prefix": "passage: ",
        "pooling": "mean",
        "trust": False,
        "note": "768차원 — 스키마 무변경 드롭인 후보",
    },
    "BAAI/bge-m3": {
        "q_prefix": "",
        "d_prefix": "",
        "pooling": "cls",
        "trust": False,
        "note": "1024차원 — 채택 시 Vector(768) 마이그레이션 필요",
    },
}

_TOP_K = 8
_MIN_RELEVANT = 3  # 정답 영화가 이보다 적은 태그는 쿼리에서 제외
_QUERY_TEMPLATE = "{label} 영화 추천해줘"

# 문서에 장르 단어가 그대로 들어가므로("장르: 스릴러") 태그명 쿼리는 어휘
# 일치만으로 풀린다 — 시맨틱 일반화를 가르는 건 아래 패러프레이즈 쿼리다
# (장르 단어를 쓰지 않는 표현 → 해당 장르 영화가 정답).
_PARAPHRASE_QUERIES: list[tuple[str, str]] = [
    ("긴장감 넘치고 손에 땀을 쥐는 영화", "스릴러"),
    ("눈물 쏙 빼는 감동적인 이야기", "드라마"),
    ("배꼽 빠지게 웃긴 거 없나", "코미디"),
    ("등골이 서늘해지는 무서운 거", "공포"),
    ("총격전이랑 추격전 많은 화끈한 영화", "액션"),
    ("설레는 연애 이야기 보고 싶어", "로맨스"),
    ("우주나 미래가 배경인 상상력 넘치는 작품", "SF"),
    ("마법과 신비한 세계관이 나오는 영화", "판타지"),
    ("범인을 쫓는 수사물 느낌", "범죄"),
    ("아이랑 같이 봐도 되는 만화 영화", "애니메이션"),
]


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--models", nargs="*", default=list(MODEL_SPECS), help="비교할 HF 모델 id 목록"
    )
    parser.add_argument("--max-queries", type=int, default=60)
    parser.add_argument(
        "--corpus-json",
        help="DB 대신 이 JSON에서 코퍼스·태그를 읽는다 — torch는 있지만 DB 드라이버가 "
        "없는 환경(노트북 ~/.venv-exaone)에서 평가를 돌리기 위한 입력. 덤프 형식은 "
        '{"corpus": [[movie_id, text], ...], "tags": [[label, movie_id], ...]}',
    )
    parser.add_argument("--batch-size", type=int, default=16)
    return parser.parse_args(argv)


async def _load_eval_data() -> tuple[list[tuple[int, str]], list[tuple[str, set[int]]]]:
    """(corpus[(movie_id, text)], queries[(text, relevant_movie_ids)])를 로컬 DB에서 구성."""
    from sqlalchemy import text

    from core.matrix.grid_oracle_database_manager import get_mova_session_factory

    factory = get_mova_session_factory()
    async with factory() as session:
        rows = (
            await session.execute(
                text(
                    "select source_ref, title, content from hub_knowledge "
                    "where source = 'mova_movie' and content <> ''"
                )
            )
        ).all()
        corpus = [(int(ref), f"{title}\n{content}".strip()) for ref, title, content in rows]

        tag_rows = (
            await session.execute(
                text("select label, movie_id from tags where movie_id is not null")
            )
        ).all()

        if not corpus:
            # 로컬 개발 DB는 hub_knowledge 미색인 스냅샷 — ingest가 만드는 것과
            # 같은 형태(제목/개봉/장르, 출연·감독은 스냅샷에 있으면)로 즉석 구성.
            movie_rows = (
                await session.execute(text("select id, title, release_year from movies"))
            ).all()
            genres_by_movie: dict[int, list[str]] = {}
            for label, movie_id in tag_rows:
                genres_by_movie.setdefault(int(movie_id), []).append(str(label))
            corpus = []
            for mid, title, year in movie_rows:
                lines = [str(title), f"개봉: {year}"]
                if genres_by_movie.get(int(mid)):
                    lines.append(f"장르: {', '.join(genres_by_movie[int(mid)])}")
                corpus.append((int(mid), "\n".join(lines)))

    corpus_ids = {mid for mid, _ in corpus}
    by_label: dict[str, set[int]] = {}
    for label, movie_id in tag_rows:
        if movie_id in corpus_ids:
            by_label.setdefault(str(label), set()).add(int(movie_id))
    queries = [
        (_QUERY_TEMPLATE.format(label=label), ids)
        for label, ids in sorted(by_label.items())
        if len(ids) >= _MIN_RELEVANT
    ]
    for query_text, genre_label in _PARAPHRASE_QUERIES:
        relevant = by_label.get(genre_label, set())
        if len(relevant) >= _MIN_RELEVANT:
            queries.append((query_text, relevant))
    return corpus, queries


def _embed(model_id: str, texts: list[str], *, batch_size: int) -> object:
    import torch
    from transformers import AutoModel, AutoTokenizer

    spec = MODEL_SPECS.get(model_id, {"pooling": "mean", "trust": False})
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=spec["trust"])
    model = AutoModel.from_pretrained(model_id, trust_remote_code=spec["trust"]).to(device).eval()

    chunks = []
    with torch.no_grad():
        for i in range(0, len(texts), batch_size):
            batch = tokenizer(
                texts[i : i + batch_size],
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            ).to(device)
            out = model(**batch).last_hidden_state
            if spec["pooling"] == "cls":
                emb = out[:, 0]
            else:
                mask = batch["attention_mask"].unsqueeze(-1)
                emb = (out * mask).sum(1) / mask.sum(1).clamp(min=1)
            chunks.append(torch.nn.functional.normalize(emb, dim=-1).cpu())
    del model
    if device == "cuda":
        torch.cuda.empty_cache()
    import torch as _t

    return _t.cat(chunks)


def _evaluate(model_id: str, corpus, queries, *, batch_size: int) -> dict[str, float]:
    import torch

    spec = MODEL_SPECS.get(model_id, {"q_prefix": "", "d_prefix": ""})
    doc_vecs = _embed(
        model_id, [spec.get("d_prefix", "") + text for _, text in corpus], batch_size=batch_size
    )
    query_vecs = _embed(
        model_id, [spec.get("q_prefix", "") + q for q, _ in queries], batch_size=batch_size
    )
    doc_ids = [mid for mid, _ in corpus]

    sims = query_vecs @ doc_vecs.T
    recall_sum = 0.0
    mrr_sum = 0.0
    for qi, (_, relevant) in enumerate(queries):
        top = torch.topk(sims[qi], k=min(_TOP_K, len(doc_ids))).indices.tolist()
        top_ids = [doc_ids[i] for i in top]
        hits = [mid for mid in top_ids if mid in relevant]
        recall_sum += len(hits) / min(len(relevant), _TOP_K)
        mrr_sum += next(
            (1.0 / (rank + 1) for rank, mid in enumerate(top_ids) if mid in relevant), 0.0
        )
    n = len(queries)
    return {"recall@8": recall_sum / n, "mrr@8": mrr_sum / n}


def _load_from_json(path: str):
    """--corpus-json 입력을 DB 경로와 같은 (corpus, queries)로 변환한다."""
    import json

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    corpus = [(int(mid), str(txt)) for mid, txt in data["corpus"]]
    corpus_ids = {mid for mid, _ in corpus}
    by_label: dict[str, set[int]] = {}
    for label, movie_id in data["tags"]:
        if int(movie_id) in corpus_ids:
            by_label.setdefault(str(label), set()).add(int(movie_id))
    queries = [
        (_QUERY_TEMPLATE.format(label=label), ids)
        for label, ids in sorted(by_label.items())
        if len(ids) >= _MIN_RELEVANT
    ]
    for query_text, genre_label in _PARAPHRASE_QUERIES:
        relevant = by_label.get(genre_label, set())
        if len(relevant) >= _MIN_RELEVANT:
            queries.append((query_text, relevant))
    return corpus, queries


async def _run(args: argparse.Namespace) -> None:

    if args.corpus_json:
        corpus, queries = _load_from_json(args.corpus_json)
    else:
        from core.matrix.vauly_keymaker_secret_manager import get_keymaker

        get_keymaker()  # .env 로드 부작용 — DB URL 주입
        corpus, queries = await _load_eval_data()
    queries = queries[: args.max_queries]
    if not corpus or not queries:
        print(f"[eval-embed] 평가 재료 부족 corpus={len(corpus)} queries={len(queries)}")
        return
    print(f"[eval-embed] corpus={len(corpus)}문서 queries={len(queries)}건 top_k={_TOP_K}")

    results: dict[str, dict[str, float]] = {}
    for model_id in args.models:
        print(f"[eval-embed] embedding … {model_id}", flush=True)
        try:
            results[model_id] = _evaluate(model_id, corpus, queries, batch_size=args.batch_size)
        except Exception as e:  # noqa: BLE001 — 한 모델 실패가 비교 전체를 막지 않게
            print(f"[eval-embed] {model_id} 실패: {e}")

    print("\n=== 결과 (높을수록 좋음) ===")
    for model_id, metric in sorted(results.items(), key=lambda kv: -kv[1]["recall@8"]):
        note = MODEL_SPECS.get(model_id, {}).get("note", "")
        print(
            f"recall@8={metric['recall@8']:.3f}  mrr@8={metric['mrr@8']:.3f}  {model_id}  ({note})"
        )


if __name__ == "__main__":
    asyncio.run(_run(_parse_args()))
