import asyncio
import base64
import logging
import os
import secrets
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logging.basicConfig(level=logging.INFO, format="%(levelname)s:\t%(message)s", force=True)
logger = logging.getLogger(__name__)

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response as StarletteResponse

_BACKEND_ROOT = Path(__file__).resolve().parent
_APPS_ROOT = _BACKEND_ROOT / "apps"
for _p in (_BACKEND_ROOT, _APPS_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from contents.adapter.inbound.api import contents_router
from core.matrix.grid_oracle_database_manager import (
    create_tables,
    dispose_engine,
    verify_connection,
)
from core.matrix.vauly_keymaker_secret_manager import get_keymaker
from dispatch.adapter.inbound.api import dispatch_router
from gildle.adapter.inbound.api import gildle_router
from mova.adapter.inbound.api import mova_router
from mova.adapter.outbound.llm.gemini_client import gemini_reply
from mova.app.ports.output.llm_errors import LLMError
from ontology.adapter.inbound.api import nlp_router, ontology_router, vision_router
from silicon_valley.adapter.inbound.api import silicon_valley_router
from titanic.adapter.inbound.api import titanic_router
from viewer.adapter.inbound.api import viewer_router
from viewer.adapter.outbound.orm.user_orm import seed_viewer_if_empty

keymaker = get_keymaker()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="??? ???")
    model: Literal["flash", "flash15", "pro"] | None = Field(
        default=None,
        description="Gemini ?? ? (??? ? .env ???)",
    )


class ChatResponse(BaseModel):
    reply: str
    refined_query: str | None = None
    keywords: list[str] = Field(default_factory=list)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from core.matrix.grid_oracle_database_manager import reload_env

    reload_env()
    try:
        ok, err = await verify_connection()
        if ok:
            try:
                await create_tables()
                await seed_viewer_if_empty()
                try:
                    from mova.adapter.outbound.pg.assistants_pg_repository import (
                        seed_assistants_if_empty,
                    )

                    await seed_assistants_if_empty()
                except Exception as ast_err:
                    logger.warning("[main] assistants ?? ??: %s", ast_err)
                try:
                    from mova.dependencies.import_provider import seed_catalog_if_sparse

                    seed_result = await seed_catalog_if_sparse()
                    if seed_result and seed_result.imported:
                        logger.info(
                            "[main] TMDB 카탈로그 시드 — imported=%s rankings=%s",
                            seed_result.imported,
                            seed_result.rankings_updated,
                        )
                except Exception as tmdb_err:
                    logger.warning("[main] TMDB 카탈로그 시드 실패: %s", tmdb_err)
                try:
                    from mova.adapter.inbound.scheduler.market_rankings_scheduler import (
                        run_chat_trend_scheduler,
                    )

                    app.state.rankings_scheduler = asyncio.create_task(run_chat_trend_scheduler())
                    logger.info("[main] chat_trend 랭킹 스케줄러 시작 (6시간 주기)")
                except Exception as sched_err:
                    logger.warning("[main] 랭킹 스케줄러 시작 실패: %s", sched_err)
                try:
                    from mova.adapter.inbound.scheduler.kofic_import_scheduler import (
                        run_kofic_import_scheduler,
                    )

                    app.state.kofic_scheduler = asyncio.create_task(run_kofic_import_scheduler())
                    logger.info("[main] KOFIC 박스오피스 자동 수입 스케줄러 시작 (24시간 주기)")
                except Exception as kofic_sched_err:
                    logger.warning("[main] KOFIC 수입 스케줄러 시작 실패: %s", kofic_sched_err)
            except Exception as e:
                logger.error(
                    "DB ???/?? ??? ?? ? DB ?? API? 503 ??: %s",
                    e,
                )
                await dispose_engine()
        else:
            logger.warning(
                "DB ?? ?? ? Mova/Viewer DB API ???. suvisdev/.env DATABASE_URL ??: %s",
                err,
            )
        # Ollama 모델 워밍업 — 콜드 스타트 제거(백그라운드, 기동 비차단)
        try:
            from core.lol.t1_mid_faker_orchestrator import get_faker_orchestrator

            app.state.faker_warmup = asyncio.create_task(
                asyncio.to_thread(get_faker_orchestrator().warmup)
            )
        except Exception as warm_err:
            logger.warning("[main] Ollama 워밍업 예약 실패: %s", warm_err)
        yield
    finally:
        scheduler_task = getattr(app.state, "rankings_scheduler", None)
        if scheduler_task is not None:
            scheduler_task.cancel()
            try:
                await scheduler_task
            except asyncio.CancelledError:
                pass
        kofic_scheduler_task = getattr(app.state, "kofic_scheduler", None)
        if kofic_scheduler_task is not None:
            kofic_scheduler_task.cancel()
            try:
                await kofic_scheduler_task
            except asyncio.CancelledError:
                pass
        await dispose_engine()


_LOGIN_HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Suvisdev API</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{min-height:100vh;background:#0d0f14;display:flex;align-items:center;justify-content:center;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;padding:1rem}
.card{width:100%;max-width:400px;background:#161a24;border:1px solid #252b3b;border-radius:24px;padding:2.5rem}
.brand{margin-bottom:2rem}
.brand-row{display:flex;align-items:center;gap:.5rem}
.brand-name{font-size:1.25rem;font-weight:700;color:#e8e8e8;letter-spacing:-.02em}
.badge{font-size:.65rem;font-family:'SF Mono','Fira Code',monospace;font-weight:600;background:#f0dc3a1a;color:#f0dc3a;border:1px solid #f0dc3a44;border-radius:6px;padding:2px 7px;letter-spacing:.05em;text-transform:uppercase}
.brand-desc{margin-top:.375rem;font-size:.8125rem;color:#6b7280}
.error{margin-bottom:1rem;padding:.625rem 1rem;background:#7f1d1d22;border:1px solid #7f1d1d55;border-radius:10px;font-size:.8125rem;color:#f87171}
.oauth{display:flex;flex-direction:column;gap:.625rem;margin-bottom:1.25rem}
.oauth-btn{display:flex;align-items:center;justify-content:center;gap:.625rem;width:100%;padding:.75rem;border-radius:14px;font-size:.875rem;font-weight:600;cursor:pointer;border:1px solid transparent;transition:filter .15s;letter-spacing:-.01em}
.oauth-btn:hover{filter:brightness(1.06)}
.oauth-btn svg{flex-shrink:0}
.oauth-google{background:#1a1f2e;border-color:#252b3b;color:#e8e8e8}
.oauth-naver{background:#03C75A;color:#fff}
.oauth-kakao{background:#FEE500;color:#191919}
.oauth-note{margin:-.25rem 0 1.25rem;text-align:center;font-size:.75rem;color:#6b7280;min-height:1em}
.divider{display:flex;align-items:center;gap:.75rem;margin-bottom:1.25rem}
.divider .line{flex:1;height:1px;background:#252b3b}
.divider span{font-size:.75rem;color:#4b5563}
.group{margin-bottom:1rem}
label{display:block;font-size:.7rem;font-weight:600;color:#9ca3af;margin-bottom:.375rem;letter-spacing:.06em;text-transform:uppercase}
input[type=text],input[type=password]{width:100%;background:#1a1f2e;border:1px solid #252b3b;border-radius:12px;padding:.75rem 1rem;color:#e8e8e8;font-size:.9375rem;outline:none;transition:border-color .15s}
input:focus{border-color:#f0dc3a66}
input::placeholder{color:#374151}
.btn{display:block;width:100%;margin-top:1.5rem;padding:.875rem;background:#f0dc3a;color:#0d0f14;font-size:.9375rem;font-weight:700;border:none;border-radius:14px;cursor:pointer;transition:background .15s;letter-spacing:-.01em}
.btn:hover{background:#e8d020}
.btn:active{background:#d4bc00}
.footer{margin-top:2rem;padding-top:1.25rem;border-top:1px solid #1e2333;display:flex;align-items:center;justify-content:center;gap:.375rem;font-size:.75rem;color:#374151}
.dot{width:6px;height:6px;background:#22c55e;border-radius:50%;flex-shrink:0}
</style>
</head>
<body>
<div class="card">
  <div class="brand">
    <div class="brand-row">
      <span class="brand-name">suvisdev</span>
      <span class="badge">API</span>
    </div>
    <p class="brand-desc">개발자 전용 대시보드입니다.</p>
  </div>
  __ERROR__
  <div class="oauth">
    <button type="button" class="oauth-btn oauth-google" data-provider="Google">
      <svg width="16" height="16" viewBox="0 0 20 20"><path fill="#4285F4" d="M19.6 10.23c0-.68-.06-1.33-.17-1.96H10v3.71h5.38a4.6 4.6 0 0 1-2 3.02v2.5h3.23c1.89-1.74 2.99-4.3 2.99-7.27Z"/><path fill="#34A853" d="M10 20c2.7 0 4.96-.89 6.61-2.42l-3.23-2.5c-.9.6-2.04.96-3.38.96-2.6 0-4.8-1.76-5.59-4.12H1.07v2.59A10 10 0 0 0 10 20Z"/><path fill="#FBBC05" d="M4.41 11.92a5.99 5.99 0 0 1 0-3.84V5.49H1.07a10 10 0 0 0 0 9.02l3.34-2.59Z"/><path fill="#EA4335" d="M10 3.96c1.47 0 2.79.5 3.83 1.5l2.87-2.87A9.55 9.55 0 0 0 10 0 10 10 0 0 0 1.07 5.49l3.34 2.59C5.2 5.72 7.4 3.96 10 3.96Z"/></svg>
      Google로 계속하기
    </button>
    <button type="button" class="oauth-btn oauth-naver" data-provider="네이버">
      <svg width="14" height="14" viewBox="0 0 20 20"><path fill="#fff" d="M11.6 10.6 8.1 5.3H5.3v9.4h3.1v-5.3l3.5 5.3h2.8V5.3h-3.1z"/></svg>
      네이버로 계속하기
    </button>
    <button type="button" class="oauth-btn oauth-kakao" data-provider="카카오">
      <svg width="16" height="16" viewBox="0 0 20 20"><path fill="#191919" d="M10 2.5c-4.42 0-8 2.79-8 6.24 0 2.2 1.46 4.14 3.66 5.25-.16.58-.58 2.1-.66 2.43-.1.4.15.4.31.29.13-.09 2.06-1.39 2.9-1.96.58.08 1.17.13 1.79.13 4.42 0 8-2.8 8-6.24s-3.58-6.14-8-6.14Z"/></svg>
      카카오로 계속하기
    </button>
  </div>
  <p class="oauth-note" id="oauth-note"></p>
  <div class="divider"><span class="line"></span><span>또는</span><span class="line"></span></div>
  <form method="post" action="/api-login">
    <input type="hidden" name="next" value="__NEXT__">
    <div class="group">
      <label for="u">아이디</label>
      <input type="text" id="u" name="username" placeholder="username" autocomplete="username" autofocus>
    </div>
    <div class="group">
      <label for="p">비밀번호</label>
      <input type="password" id="p" name="password" placeholder="••••••••" autocomplete="current-password">
    </div>
    <button type="submit" class="btn">로그인</button>
  </form>
  <div class="footer">
    <span class="dot"></span>
    <span>api.suvisdev.cloud</span>
  </div>
</div>
<script>
document.querySelectorAll(".oauth-btn").forEach(function (btn) {
  btn.addEventListener("click", function () {
    document.getElementById("oauth-note").textContent = btn.dataset.provider + " 로그인은 준비 중입니다.";
  });
});
</script>
</body>
</html>"""


def _render_login(next_path: str, error: bool = False) -> str:
    safe = next_path if next_path.startswith("/") and not next_path.startswith("//") else "/docs"
    err = '<div class="error">아이디 또는 비밀번호가 올바르지 않습니다.</div>' if error else ""
    return _LOGIN_HTML.replace("__NEXT__", safe).replace("__ERROR__", err)


class _ApiAuthMiddleware(BaseHTTPMiddleware):
    """개발자 대시보드(/docs, /redoc, /openapi.json)만 막는다.

    프론트엔드(suvis)가 실제로 호출하는 mova/viewer/titanic 등 나머지 API 경로는
    이 게이트와 무관하게 항상 공개 상태여야 한다 — 여기 걸리면 로그인·채팅 등
    실서비스 전체가 막힌다.
    """

    _GATED = {"/docs", "/redoc", "/openapi.json"}
    _BYPASS = {"/api-login", "/api-logout", "/favicon.ico"}
    _COOKIE = "api_auth"

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> StarletteResponse:
        username = os.getenv("API_USERNAME", "")
        password = os.getenv("API_PASSWORD", "")
        if not username or request.url.path not in self._GATED:
            return await call_next(request)
        if request.url.path in self._BYPASS:
            return await call_next(request)
        expected = base64.b64encode(f"{username}:{password}".encode()).decode()
        cookie = request.cookies.get(self._COOKIE, "")
        if cookie and secrets.compare_digest(cookie.encode(), expected.encode()):
            return await call_next(request)
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Basic "):
            try:
                decoded = base64.b64decode(auth[6:]).decode("utf-8")
                u, _, p = decoded.partition(":")
                if secrets.compare_digest(u.encode(), username.encode()) and secrets.compare_digest(
                    p.encode(), password.encode()
                ):
                    return await call_next(request)
            except Exception:
                pass
        return RedirectResponse(url=f"/api-login?next={request.url.path}", status_code=302)


app = FastAPI(title="Suvisdev Main Page", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(_ApiAuthMiddleware)


@app.middleware("http")
async def request_path_logger(request: Request, call_next):
    response = await call_next(request)
    logger.info(
        "%s %s -> %s",
        request.method,
        request.url.path,
        response.status_code,
    )
    return response


app.include_router(mova_router)
app.include_router(titanic_router, prefix="/api")
app.include_router(gildle_router, prefix="/api")
app.include_router(viewer_router)
app.include_router(silicon_valley_router, prefix="/api/v1")
app.include_router(dispatch_router, prefix="/api/v1")
app.include_router(contents_router, prefix="/api/v1")
app.include_router(vision_router, prefix="/api")
app.include_router(ontology_router, prefix="/api")
app.include_router(nlp_router, prefix="/api")


@app.get("/api-login", response_class=HTMLResponse, include_in_schema=False)
async def login_page(next: str = "/docs", error: bool = False) -> HTMLResponse:
    return HTMLResponse(_render_login(next, error))


@app.post("/api-login", include_in_schema=False)
async def login_submit(
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form(default="/docs"),
) -> RedirectResponse:
    api_user = os.getenv("API_USERNAME", "")
    api_pass = os.getenv("API_PASSWORD", "")
    safe_next = next if next.startswith("/") and not next.startswith("//") else "/docs"
    if not api_user or (
        secrets.compare_digest(username.encode(), api_user.encode())
        and secrets.compare_digest(password.encode(), api_pass.encode())
    ):
        token = base64.b64encode(f"{username}:{password}".encode()).decode()
        resp = RedirectResponse(url=safe_next, status_code=303)
        resp.set_cookie(
            "api_auth", token, max_age=2 * 3600, httponly=True, samesite="strict", path="/"
        )
        return resp
    return RedirectResponse(url=f"/api-login?next={safe_next}&error=1", status_code=303)


@app.get("/api-logout", include_in_schema=False)
async def logout() -> RedirectResponse:
    resp = RedirectResponse(url="/api-login", status_code=303)
    resp.delete_cookie("api_auth", path="/")
    return resp


@app.get("/")
def read_root():
    return {"message": "FAST API ??? ??", "docs": "/docs"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    """?? Gemini ?? (?? ?? ? Mova ??? ??)."""
    try:
        text = gemini_reply(req.message, req.model)
    except LLMError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    return ChatResponse(reply=text)


if __name__ == "__main__":
    import selectors

    import uvicorn

    config = uvicorn.Config(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True,
    )
    server = uvicorn.Server(config)
    if sys.platform == "win32":
        with asyncio.Runner(
            loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
        ) as runner:
            runner.run(server.serve())
    else:
        asyncio.run(server.serve())
