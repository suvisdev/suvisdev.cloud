from __future__ import annotations

import sys
import unittest
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import AsyncMock, Mock

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from mova.app.dtos.harvest_ingest_dto import HarvestRow  # noqa: E402
from mova.app.ports.output.harvest_reader_port import HarvestReaderPort  # noqa: E402
from mova.app.use_cases.harvest_ingest_interactor import HarvestIngestInteractor  # noqa: E402
from ontology.app.dtos.hub_knowledge_dto import HubKnowledgeUpsertCommand  # noqa: E402


class _FakeReader(HarvestReaderPort):
    def __init__(self, rows: list[HarvestRow]) -> None:
        self._rows = rows

    def read(self, path: Path) -> Iterator[HarvestRow]:
        return iter(self._rows)


class HarvestIngestInteractorTests(unittest.IsolatedAsyncioTestCase):
    async def test_kowiki_content_combines_lead_and_sections(self) -> None:
        row = HarvestRow(
            source="kowiki",
            url="https://ko.wikipedia.org/wiki/x",
            title="영화 X",
            content="리드 문단",
            sections={"줄거리": "줄거리 본문"},
        )
        hub_rag = AsyncMock()
        movies = AsyncMock()
        movies.find_by_title.return_value = None
        interactor = HarvestIngestInteractor(
            reader=_FakeReader([row]), movies=movies, hub_rag=hub_rag
        )

        result = await interactor.ingest(Path("unused.jsonl"))

        self.assertEqual(result.total, 1)
        self.assertEqual(result.ingested, 1)
        self.assertEqual(result.unmatched, 1)
        command: HubKnowledgeUpsertCommand = hub_rag.ingest_movie.call_args.args[0]
        self.assertEqual(command.source, "kowiki")
        self.assertEqual(command.source_ref, row.url)
        self.assertIn("리드 문단", command.content)
        self.assertIn("[줄거리]\n줄거리 본문", command.content)

    async def test_tmdb_content_combines_overview_and_infobox(self) -> None:
        row = HarvestRow(
            source="tmdb",
            url="https://www.themoviedb.org/movie/1",
            title="영화 Y",
            content="overview text",
            infobox={"감독": "홍길동", "장르": "드라마"},
        )
        hub_rag = AsyncMock()
        movies = AsyncMock()
        movies.find_by_title.return_value = Mock()
        interactor = HarvestIngestInteractor(
            reader=_FakeReader([row]), movies=movies, hub_rag=hub_rag
        )

        result = await interactor.ingest(Path("unused.jsonl"))

        self.assertEqual(result.matched, 1)
        command: HubKnowledgeUpsertCommand = hub_rag.ingest_movie.call_args.args[0]
        self.assertIn("overview text", command.content)
        self.assertIn("감독: 홍길동", command.content)

    async def test_kobis_content_combines_stats_and_metrics(self) -> None:
        row = HarvestRow(
            source="kobis",
            url="daily:20260715:20183782",
            title="호프",
            content="감독: 홍길동\n장르: 드라마",
            metrics={"rank": 1.0, "audi_cnt": 152030.0},
        )
        hub_rag = AsyncMock()
        movies = AsyncMock()
        movies.find_by_title.return_value = None
        interactor = HarvestIngestInteractor(
            reader=_FakeReader([row]), movies=movies, hub_rag=hub_rag
        )

        await interactor.ingest(Path("unused.jsonl"))

        command: HubKnowledgeUpsertCommand = hub_rag.ingest_movie.call_args.args[0]
        self.assertIn("순위: 1", command.content)
        self.assertIn("일일 관객수: 152030", command.content)

    async def test_google_news_content_used_as_is(self) -> None:
        row = HarvestRow(
            source="google_news",
            url="https://news.google.com/x",
            title="영화 개봉 소식",
            content="영화 개봉 소식\n요약 텍스트",
        )
        hub_rag = AsyncMock()
        movies = AsyncMock()
        movies.find_by_title.return_value = None
        interactor = HarvestIngestInteractor(
            reader=_FakeReader([row]), movies=movies, hub_rag=hub_rag
        )

        await interactor.ingest(Path("unused.jsonl"))

        command: HubKnowledgeUpsertCommand = hub_rag.ingest_movie.call_args.args[0]
        self.assertEqual(command.content, "영화 개봉 소식\n요약 텍스트")

    async def test_skips_rows_missing_url_or_title(self) -> None:
        rows = [
            HarvestRow(source="kobis", url="", title="제목만있음", content="c"),
            HarvestRow(source="kobis", url="u", title="", content="c"),
        ]
        hub_rag = AsyncMock()
        movies = AsyncMock()
        interactor = HarvestIngestInteractor(
            reader=_FakeReader(rows), movies=movies, hub_rag=hub_rag
        )

        result = await interactor.ingest(Path("unused.jsonl"))

        self.assertEqual(result.total, 2)
        self.assertEqual(result.ingested, 0)
        hub_rag.ingest_movie.assert_not_awaited()

    async def test_matched_and_unmatched_counts_reported(self) -> None:
        rows = [
            HarvestRow(source="google_news", url="u1", title="매칭됨", content="c1"),
            HarvestRow(source="google_news", url="u2", title="미매칭", content="c2"),
        ]
        hub_rag = AsyncMock()
        movies = AsyncMock()
        movies.find_by_title.side_effect = [Mock(), None]
        interactor = HarvestIngestInteractor(
            reader=_FakeReader(rows), movies=movies, hub_rag=hub_rag
        )

        result = await interactor.ingest(Path("unused.jsonl"))

        self.assertEqual(result.matched, 1)
        self.assertEqual(result.unmatched, 1)
        self.assertEqual(result.ingested, 2)


if __name__ == "__main__":
    unittest.main()
