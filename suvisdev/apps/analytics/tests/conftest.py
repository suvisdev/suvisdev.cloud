import sys
from pathlib import Path

_here = Path(__file__).parent  # apps/analytics/tests/

_paths = [
    _here.parent,                   # apps/analytics/ → tests.* (Fake 포트) 임포트
    _here.parent.parent,            # apps/      → analytics.* 임포트
    _here.parent.parent.parent,     # suvisdev/  → core.* 임포트
]
for _p in _paths:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
