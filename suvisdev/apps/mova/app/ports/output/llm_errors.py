"""LLM 출력 포트 실패 예외 — ``llm_output_port``·``gemini_client`` 계약의 오류 면.

아웃바운드 LLM 어댑터는 FastAPI(HTTPException)에 의존하지 않는다.
인바운드 라우터가 ``HTTPException``으로 변환한다 (``apps/mova/_docs/CLAUDE.md`` §B.4).
``core.matrix.weather_reader.WeatherReaderError`` 와 동일하게 ``status_code`` 를 실어 보낸다.
"""

from __future__ import annotations


class LLMError(Exception):
    """LLM 호출 실패 기본 예외."""

    status_code = 503

    def __init__(self, detail: str, *, status_code: int | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        if status_code is not None:
            self.status_code = status_code


class LLMTimeoutError(LLMError):
    """LLM 응답 타임아웃."""

    status_code = 504


class LLMUnavailableError(LLMError):
    """LLM 서비스 사용 불가 (API 키 미설정·모델 초기화 실패 등)."""

    status_code = 503
