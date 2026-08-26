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

from typer.testing import CliRunner  # noqa: E402

from ontology.adapter.inbound.cli import app as cli_app_module  # noqa: E402
from ontology.test.fakes.fake_site_scraper import FakeSiteScraper  # noqa: E402

runner = CliRunner()


class HarvesterCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_registry = dict(cli_app_module.SITE_REGISTRY)
        cli_app_module.SITE_REGISTRY.clear()
        cli_app_module.SITE_REGISTRY["fake"] = FakeSiteScraper
        self._orig_build_site_scraper = cli_app_module.build_site_scraper
        cli_app_module.build_site_scraper = lambda site_id, *, rate, dedup: FakeSiteScraper()

    def tearDown(self) -> None:
        cli_app_module.SITE_REGISTRY.clear()
        cli_app_module.SITE_REGISTRY.update(self._orig_registry)
        cli_app_module.build_site_scraper = self._orig_build_site_scraper

    def test_scrape_writes_jsonl_with_fake_site(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "out.jsonl"
            result = runner.invoke(
                cli_app_module.app,
                [
                    "scrape",
                    "--site",
                    "fake",
                    "--keyword",
                    "패터슨",
                    "--limit",
                    "5",
                    "--out",
                    str(out_path),
                ],
            )

            self.assertEqual(result.exit_code, 0, msg=result.output)
            lines = out_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 5)
            for line in lines:
                json.loads(line)

    def test_scrape_unknown_site_exits_with_code_2(self) -> None:
        cli_app_module.SITE_REGISTRY.clear()
        cli_app_module.SITE_REGISTRY["fake"] = FakeSiteScraper

        result = runner.invoke(
            cli_app_module.app,
            ["scrape", "--site", "nope", "--keyword", "k", "--limit", "1"],
        )

        self.assertEqual(result.exit_code, 2)
        self.assertIn("등록되지 않은 사이트", result.output)

    def test_sites_lists_registered_sites(self) -> None:
        result = runner.invoke(cli_app_module.app, ["sites"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("fake", result.output)
        self.assertIn("httpx", result.output)


if __name__ == "__main__":
    unittest.main()
