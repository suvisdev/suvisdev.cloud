"""apps/ontology/crawl_config.yaml에서 CrawlPolicy 목록을 읽는 CrawlPolicyPort 구현체."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ontology.app.dtos.crawl_schedule_dto import CrawlPolicy
from ontology.app.ports.output.crawl_policy_port import CrawlPolicyPort

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[3] / "crawl_config.yaml"


class YamlCrawlPolicyAdapter(CrawlPolicyPort):
    def __init__(self, *, config_path: Path = _DEFAULT_CONFIG_PATH) -> None:
        self._config_path = config_path

    def get_policies(self) -> list[CrawlPolicy]:
        if not self._config_path.exists():
            return []
        raw = yaml.safe_load(self._config_path.read_text(encoding="utf-8")) or {}
        entries: list[dict[str, Any]] = raw.get("policies") or []
        return [
            CrawlPolicy(
                site_id=entry["site"],
                keywords=tuple(entry["keywords"]),
                interval_minutes=int(entry["interval_minutes"]),
                limit_per_keyword=(
                    int(entry["limit_per_keyword"]) if "limit_per_keyword" in entry else None
                ),
            )
            for entry in entries
        ]
