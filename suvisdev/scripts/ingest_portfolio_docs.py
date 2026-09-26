"""공개 문서(마크다운)를 hub_knowledge(source='portfolio_doc')에 색인 — 홈 포트폴리오 AI 채팅 근거.

Usage (suvisdev 폴더에서):
  python scripts/ingest_portfolio_docs.py datasets/portfolio_corpus ~/projects/suvisjk/about.markdown \
      ~/projects/suvisjk/_posts --reset
  --reset                   시작 전 기존 source='portfolio_doc' 로우 전부 삭제(재색인 시 권장 — 청크 수가
                            줄어든 파일의 잔여 청크가 남지 않게).
  --dry-run                 DB에 쓰지 않고 파일별 청크 수·제목만 출력.
  --embedding-backend       ollama|gemini. 미지정 시 EMBEDDING_BACKEND(기본 ollama). 저장된 벡터와
                            같은 백엔드여야 한다(의미 공간 불일치 사고 2026-08-07).
경로 인자는 파일 또는 디렉터리(*.md, *.markdown 재귀). **공개해도 되는 문서만** 넘길 것 — 여기 넣은
내용은 익명 방문자의 질문에 그대로 답변 근거로 쓰인다(연락처·내부 인프라 문서 금지).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import re
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
_APPS = _BACKEND / "apps"
for _p in (_BACKEND, _APPS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

logging.basicConfig(level=logging.WARNING, format="%(levelname)s:\t%(message)s")

SOURCE = "portfolio_doc"
MAX_CHARS = 1500
MIN_CHARS = 200
_FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
_TITLE_LINE = re.compile(r"^title:\s*(.+)$", re.M)
_H1 = re.compile(r"^#\s+(.+)$", re.M)
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)


def _doc_title(front: str, body: str, fallback: str) -> str:
    m = _TITLE_LINE.search(front)
    if m:
        return m.group(1).strip().strip("'\"")
    h = _H1.search(body)
    return h.group(1).strip() if h else fallback


def _split_long(text: str) -> list[str]:
    if len(text) <= MAX_CHARS:
        return [text]
    out: list[str] = []
    buf = ""
    for para in re.split(r"\n\s*\n", text):
        if buf and len(buf) + len(para) + 2 > MAX_CHARS:
            out.append(buf)
            buf = para
        else:
            buf = f"{buf}\n\n{para}" if buf else para
    if buf:
        out.append(buf)
    return out


def chunk_markdown(text: str, *, fallback_title: str) -> list[tuple[str, str]]:
    """(제목, 본문) 청크 목록. front matter 제거 → `## ` 헤딩 단위 → 1500자 초과 재분할 → 200자 미만 병합."""
    front = ""
    m = _FRONT_MATTER.match(text)
    if m:
        front, text = m.group(1), text[m.end() :]
    text = _HTML_COMMENT.sub("", text)  # 편집용 주석은 근거가 아니다
    doc_title = _doc_title(front, text, fallback_title)
    sections: list[tuple[str, str]] = []
    heading = doc_title
    buf: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if buf:
                sections.append((heading, "\n".join(buf).strip()))
            heading = f"{doc_title} — {line[3:].strip()}"
            buf = []
        else:
            buf.append(line)
    if buf:
        sections.append((heading, "\n".join(buf).strip()))

    chunks: list[tuple[str, str]] = []
    for title, body in sections:
        body = re.sub(r"^#\s+.+\n", "", body).strip()
        if not body:
            continue
        for piece in _split_long(body):
            if len(piece.strip()) < 20:  # 헤딩만 남은 빈 절
                continue
            if chunks and len(piece) < MIN_CHARS:
                prev_title, prev_body = chunks[-1]
                chunks[-1] = (prev_title, f"{prev_body}\n\n{piece}")
            else:
                chunks.append((title, piece))
    return chunks


def collect_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        p = Path(raw).expanduser()
        if p.is_dir():
            files.extend(sorted(q for q in p.rglob("*") if q.suffix in (".md", ".markdown")))
        elif p.is_file():
            files.append(p)
        else:
            print(f"[skip] 없는 경로: {p}")
    return files


async def main(args: argparse.Namespace) -> None:
    files = collect_files(args.paths)
    plan: list[tuple[Path, list[tuple[str, str]]]] = []
    for f in files:
        chunks = chunk_markdown(f.read_text(encoding="utf-8"), fallback_title=f.stem)
        plan.append((f, chunks))
        print(f"{f.name}: {len(chunks)}청크" + ("" if chunks else " (본문 없음 — 건너뜀)"))
        if args.dry_run:
            for i, (t, b) in enumerate(chunks):
                print(f"   #{i} {t} ({len(b)}자)")
    total = sum(len(c) for _, c in plan)
    print(f"파일 {len(files)}개, 청크 {total}개")
    if args.dry_run:
        return

    from sqlalchemy import delete

    from core.matrix.grid_oracle_database_manager import get_mova_session_factory
    from core.matrix.vauly_keymaker_secret_manager import get_keymaker
    from ontology.adapter.outbound.llm.gemini_embedding_adapter import GeminiEmbeddingAdapter
    from ontology.adapter.outbound.llm.ollama_embedding_adapter import OllamaEmbeddingAdapter
    from ontology.adapter.outbound.orm.hub_knowledge_orm import HubKnowledgeOrm
    from ontology.adapter.outbound.repositories.hub_knowledge_repository import (
        HubKnowledgeRepository,
    )
    from ontology.app.dtos.hub_knowledge_dto import HubKnowledgeUpsertCommand
    from ontology.app.use_cases.hub_rag_interactor import HubRagInteractor

    get_keymaker()  # .env 로드 부작용 — MOVA_DATABASE_URL·GEMINI 키(ingest_hub_knowledge.py와 동일)
    backend = args.embedding_backend or os.getenv("EMBEDDING_BACKEND", "ollama").strip().lower()
    embedding = GeminiEmbeddingAdapter() if backend == "gemini" else OllamaEmbeddingAdapter()

    async with get_mova_session_factory()() as session:
        # 이름은 ingest_movie지만 source/source_ref가 자유인 범용 upsert(임베딩 실패는 False).
        hub = HubRagInteractor(repository=HubKnowledgeRepository(session), embedding=embedding)
        if args.reset:
            result = await session.execute(
                delete(HubKnowledgeOrm).where(HubKnowledgeOrm.source == SOURCE)
            )
            await session.commit()
            print(f"[reset] 기존 {SOURCE} 로우 {result.rowcount}건 삭제")

        succeeded, failed = 0, []
        for f, chunks in plan:
            stem = f.stem[:100]
            for i, (title, body) in enumerate(chunks):
                command = HubKnowledgeUpsertCommand(
                    source=SOURCE, source_ref=f"portfolio:{stem}#{i}", title=title, content=body
                )
                ok = False
                for attempt in range(4):
                    ok = await hub.ingest_movie(command)
                    if ok:
                        break
                    await asyncio.sleep(2 * (2**attempt))
                if ok:
                    succeeded += 1
                else:
                    failed.append(command.source_ref)
            await session.commit()
            print(f"  완료: {f.name}")
        print(f"전체 완료 succeeded={succeeded} failed={len(failed)} / {total}")
        for ref in failed:
            print(f"  실패: {ref}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("paths", nargs="+", help="마크다운 파일 또는 디렉터리")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--embedding-backend", choices=["ollama", "gemini"], default=None)
    asyncio.run(main(parser.parse_args()))
