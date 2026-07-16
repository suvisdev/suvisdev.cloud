"""사이트+키워드 스크래퍼 CLI 진입점 — ontology.adapter.inbound.cli.app을 그대로 실행한다.

Usage (suvisdev 폴더에서):
  python scripts/harvester_cli.py scrape --site kowiki --keyword "패터슨" --limit 5
  python scripts/harvester_cli.py crawl-batch
  python scripts/harvester_cli.py interactive
  python scripts/harvester_cli.py sites
"""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
_APPS = _BACKEND / "apps"
for _p in (_BACKEND, _APPS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from ontology.adapter.inbound.cli.app import app  # noqa: E402

if __name__ == "__main__":
    app()
