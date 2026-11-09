"""공격 시험용 임시 서버 — 운영과 같은 라우터·규칙·모델에 메모리 사이트·로그만 끼운다.

운영 DB를 건드리지 않고 재학습 데이터도 더럽히지 않는다. 사용법은 attack_eval.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "test"))
from fakes import _FakeEventRepository, _FakeSiteRepository, make_site  # noqa: E402

from deolmi.adapter.inbound.api import deolmi_router  # noqa: E402
from deolmi.app.use_cases.score_interactor import ScoreInteractor  # noqa: E402
from deolmi.dependencies import deolmi_provider  # noqa: E402

SITE_KEY, SECRET = "pk_eval", "sk_eval"

_PAGE = f"""<!doctype html><meta charset="utf-8"><title>예매 시험</title>
<script src="/api/deolmi/sdk.js"></script>
<div style="padding:60px;font-family:sans-serif">
  <p><button id="seat" type="button">A열 7번 좌석</button></p>
  <p><input id="name" placeholder="이름" style="padding:8px"></p>
  <p><input id="phone" placeholder="연락처" style="padding:8px"></p>
  <p style="margin-top:200px"><button id="buy" type="button">예매하기</button></p>
  <pre id="out"></pre>
</div>
<script>
  const dm = Deolmi.init({{ endpoint: location.origin, siteKey: "{SITE_KEY}" }});
  document.getElementById("buy").addEventListener("click", async () => {{
    const signals = dm.features();
    const result = await dm.score();
    window.__result = {{ ...result, signals }};
    document.getElementById("out").textContent = JSON.stringify({{ verdict: result.verdict, ...signals }}, null, 1);
  }});
</script>"""

app = FastAPI()
app.include_router(deolmi_router, prefix="/api")
_sites = _FakeSiteRepository(make_site(SITE_KEY, SECRET, ("localhost",)))
_events = _FakeEventRepository()
app.dependency_overrides[deolmi_provider.get_score_use_case] = lambda: ScoreInteractor(
    sites=_sites,
    events=_events,
    model=deolmi_provider._model(),
    tokens=deolmi_provider._tokens(),
    velocity=deolmi_provider._velocity(),
)


@app.get("/page", response_class=HTMLResponse)
def page() -> str:
    return _PAGE
