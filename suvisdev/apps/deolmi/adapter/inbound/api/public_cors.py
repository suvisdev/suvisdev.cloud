"""/score만 모든 출처에 CORS를 연다.

전역 CORSMiddleware(main.py)는 suvisdev 프론트만 허용하는데, 덜미 SDK는 고객 사이트에서
/score를 부른다. 그래서 이 경로만 가장 바깥에서 가로채 별도 CORS(자격증명 없음)로 처리한다.
출처 통제는 사이트별 허용 도메인(origin_policy)이 한다. /verify는 고객 서버가 부르므로 CORS 불필요.
"""

from __future__ import annotations

from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

PUBLIC_SCORE_PATH = "/api/deolmi/score"


class DeolmiPublicCorsMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app
        self._cors = CORSMiddleware(
            app,
            allow_origins=["*"],
            allow_methods=["POST"],
            allow_headers=["content-type"],
            allow_credentials=False,
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["path"] == PUBLIC_SCORE_PATH:
            await self._cors(scope, receive, send)
        else:
            await self._app(scope, receive, send)
