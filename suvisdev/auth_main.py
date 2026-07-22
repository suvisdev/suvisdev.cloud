import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent
_APPS_ROOT = _BACKEND_ROOT / "apps"
for _p in (_BACKEND_ROOT, _APPS_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth.router import router as auth_router

app = FastAPI(
    title="Suvisdev Auth Gateway",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# 인증 게이트웨이는 main.py(backend)의 allow_origins=["*"]를 그대로 쓰지 않는다 —
# 민감한 엔드포인트(/auth/exchange 등)라 명시적 도메인만 허용한다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://suvisdev.cloud"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.get("/healthz")
async def healthz() -> dict[str, bool]:
    return {"ok": True}
