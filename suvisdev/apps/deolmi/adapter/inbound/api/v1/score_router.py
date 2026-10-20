"""고객 사이트가 부르는 공개 API.

/score·/sdk.js는 무인증이 의도다 — 고객 사이트의 익명 방문자 브라우저가 공개 키(pk_)로
부른다. 들어올 수 있는 것은 행동 수치(SignalsSchema)뿐이고, 남의 사이트에서 쓰는 것은
사이트별 허용 도메인(Origin)으로 막는다. /verify는 고객 서버가 비밀 키(sk_)로 인증한다.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import FileResponse

from deolmi.adapter.inbound.api.schemas.score_schema import (
    ScoreRequestSchema,
    ScoreResponseSchema,
    ScoreResultSchema,
    VerifyRequestSchema,
)
from deolmi.app.dtos.score_dto import ScoreCommand, VerifyCommand
from deolmi.app.errors import (
    BadSecretError,
    OriginNotAllowedError,
    TokenExpiredError,
    TokenInvalidError,
    TokenReusedError,
    TokenStoreUnavailableError,
    UnknownSiteError,
)
from deolmi.app.ports.input.score_use_case import ScoreUseCase
from deolmi.dependencies.deolmi_provider import get_score_use_case

score_router = APIRouter(tags=["deolmi"])

_SDK_PATH = Path(__file__).resolve().parents[4] / "sdk" / "deolmi.js"

_ERROR_STATUS: dict[type[Exception], tuple[int, str]] = {
    UnknownSiteError: (401, "unknown site_key"),
    OriginNotAllowedError: (403, "origin not allowed"),
    BadSecretError: (401, "bad secret"),
    TokenExpiredError: (400, "token expired"),
    TokenInvalidError: (401, "invalid token"),
    TokenReusedError: (400, "token already used"),
    TokenStoreUnavailableError: (503, "token store unavailable"),
}


def _client_ip(request: Request) -> str:
    # mova/ontology rate_limit와 같은 규칙: CF-Connecting-IP가 신뢰 가능한 원 IP,
    # X-Forwarded-For는 첫 요소가 위조 가능해 마지막 요소를 쓴다.
    cf_ip = request.headers.get("cf-connecting-ip", "").strip()
    if cf_ip:
        return cf_ip
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def _http_error(e: Exception) -> HTTPException:
    status, detail = _ERROR_STATUS[type(e)]
    return HTTPException(status_code=status, detail=detail)


@score_router.get("/sdk.js", include_in_schema=False)
async def sdk() -> FileResponse:
    return FileResponse(_SDK_PATH, media_type="application/javascript")


@score_router.post("/score", response_model=ScoreResponseSchema)
async def score(
    req: ScoreRequestSchema,
    request: Request,
    background_tasks: BackgroundTasks,
    use_case: ScoreUseCase = Depends(get_score_use_case),
) -> ScoreResponseSchema:
    command = ScoreCommand.from_schema(req, request.headers.get("origin"), _client_ip(request))
    try:
        issued = await use_case.score(command)
    except (UnknownSiteError, OriginNotAllowedError) as e:
        raise _http_error(e) from e
    # 로그는 응답을 보낸 뒤 쓴다 — 폭주 때 응답이 DB 쓰기를 기다리지 않게.
    background_tasks.add_task(use_case.record_event, issued.event)
    return issued.to_schema()


@score_router.post("/verify", response_model=ScoreResultSchema)
async def verify(
    req: VerifyRequestSchema,
    use_case: ScoreUseCase = Depends(get_score_use_case),
) -> ScoreResultSchema:
    try:
        return (await use_case.verify(VerifyCommand.from_schema(req))).to_schema()
    except (
        BadSecretError,
        TokenExpiredError,
        TokenInvalidError,
        TokenReusedError,
        TokenStoreUnavailableError,
    ) as e:
        raise _http_error(e) from e
