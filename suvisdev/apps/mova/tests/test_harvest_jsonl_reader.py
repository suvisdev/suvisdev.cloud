from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from mova.adapter.outbound.harvest.harvest_jsonl_reader import (  # noqa: E402
    HarvestJsonlReaderAdapter,
)

_HARVEST_MODULE_PATH = (
    ROOT / "apps" / "mova" / "adapter" / "outbound" / "harvest" / "harvest_jsonl_reader.py"
)


class HarvestJsonlReaderAdapterTests(unittest.TestCase):
    def test_parses_lines_into_harvest_rows(self) -> None:
        lines = [
            {
                "source": "kowiki",
                "url": "https://ko.wikipedia.org/wiki/x",
                "title": "영화 X",
                "content": "리드 문단",
                "sections": {"줄거리": "줄거리 본문"},
            },
            {
                "source": "tmdb",
                "url": "https://www.themoviedb.org/movie/1",
                "title": "영화 Y",
                "content": "overview",
                "infobox": {"감독": "홍길동"},
                "external_ids": {"tmdb_id": "1"},
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.jsonl"
            path.write_text(
                "\n".join(json.dumps(line, ensure_ascii=False) for line in lines) + "\n",
                encoding="utf-8",
            )

            rows = list(HarvestJsonlReaderAdapter().read(path))

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].source, "kowiki")
        self.assertEqual(rows[0].sections, {"줄거리": "줄거리 본문"})
        self.assertEqual(rows[1].infobox, {"감독": "홍길동"})
        self.assertEqual(rows[1].external_ids, {"tmdb_id": "1"})

    def test_skips_blank_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.jsonl"
            path.write_text(
                '{"source": "kobis", "url": "u", "title": "t", "content": "c"}\n\n\n',
                encoding="utf-8",
            )

            rows = list(HarvestJsonlReaderAdapter().read(path))

        self.assertEqual(len(rows), 1)

    def test_does_not_import_harvester_modules(self) -> None:
        import_lines = [
            line
            for line in _HARVEST_MODULE_PATH.read_text(encoding="utf-8").splitlines()
            if line.startswith("import ") or line.startswith("from ")
        ]
        for line in import_lines:
            self.assertNotIn("ontology.app.dtos.scrape_dto", line)
            self.assertNotIn("ontology.adapter.outbound.scraper", line)


if __name__ == "__main__":
    unittest.main()
