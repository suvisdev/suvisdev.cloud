import sys
from pathlib import Path

import pytest

_here = Path(__file__).parent  # apps/titanic/tests/

_paths = [
    _here,                          # korean_ai 임포트
    _here.parent.parent,            # apps/ → titanic.* 임포트
    _here.parent.parent.parent,     # suvisdev/ → core.* 임포트
    _here.parent.parent.parent.parent,  # cloud.suvisdev/ → tailor.* 임포트
]
for _p in _paths:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


def pytest_collection_modifyitems(config, items):
    if not config.option.markexpr:
        skip = pytest.mark.skip(reason="ollama 서버 필요: python -m pytest -m ollama 로 실행")
        for item in items:
            if item.get_closest_marker("ollama"):
                item.add_marker(skip)
