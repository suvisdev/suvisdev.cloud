import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent
_APPS_ROOT = _BACKEND_ROOT / "apps"
for _p in (_BACKEND_ROOT, _APPS_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from fastapi import FastAPI

from auth.router import router as auth_router

app = FastAPI(
    title="Suvisdev Auth Gateway",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.include_router(auth_router)


@app.get("/healthz")
async def healthz() -> dict[str, bool]:
    return {"ok": True}
