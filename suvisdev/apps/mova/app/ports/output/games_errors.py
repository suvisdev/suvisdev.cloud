"""미니게임 예외 — 인바운드 라우터가 HTTPException으로 변환한다(§P: 인터랙터는 HTTP를 모른다)."""

from __future__ import annotations


class GamesError(Exception):
    """게임 요청 오류. status_code는 라우터가 그대로 쓴다(400 잘못된 입력 · 503 문제용 영화 부족)."""

    def __init__(self, detail: str, *, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
