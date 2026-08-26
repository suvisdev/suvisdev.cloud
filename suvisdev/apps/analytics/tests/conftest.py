import sys
from pathlib import Path

_here = Path(__file__).parent  # apps/analytics/tests/

# apps/analytics/(bare "tests" 패키지 진입점)는 넣지 않는다 — gildle 등 다른 앱도
# 같은 방식으로 "tests"를 등록해서 전체 스위트를 같이 돌리면 이름이 충돌한다
# (먼저 import되는 쪽이 이긴다). fakes는 analytics.tests.app.fakes로 패키지
# 경로를 통해 임포트한다.
_paths = [
    _here.parent.parent,  # apps/      → analytics.* 임포트
    _here.parent.parent.parent,  # suvisdev/  → core.* 임포트
]
for _p in _paths:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
