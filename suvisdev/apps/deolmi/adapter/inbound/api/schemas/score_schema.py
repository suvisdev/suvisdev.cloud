from __future__ import annotations

import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# 상한 — 사람이 한 페이지에서 낼 수 없는 값은 422로 막는다(무한대·거대 수가 모델·JSONB에서 500을 내지 않게).
_MAX_COUNT = 1_000_000  # 이벤트 수
_MAX_PX = 1_000_000_000.0  # 이동 거리(px)
_MAX_MS = 1_000_000_000.0  # 간격·체류(ms) — 약 11.5일


def _drop_non_finite(data: Any) -> Any:
    """JSON의 1e309는 inf가 된다. pydantic이 422를 내도 FastAPI 기본 처리기가 오류에 입력값(inf)을
    그대로 실어 JSON으로 쓰다 500이 난다 — 그래서 검증 전에 None으로 바꿔 '숫자 아님' 422로 떨군다."""
    if isinstance(data, float) and not math.isfinite(data):
        return None
    if isinstance(data, dict):
        return {k: _drop_non_finite(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_drop_non_finite(v) for v in data]
    return data


class _PublicRequest(BaseModel):
    """공개 요청 바디 — 어디에 inf가 들어와도(중첩·목록 포함) 500이 아니라 422."""

    @model_validator(mode="before")
    @classmethod
    def _finite_only(cls, data: Any) -> Any:
        return _drop_non_finite(data)


class SignalsSchema(BaseModel):
    """SDK가 모으는 행동 신호. 입력 글자는 없다 — 리듬·궤적 수치만.
    모르는 키는 버린다(로그에 임의 값이 쌓이지 않게). NaN·무한대는 받지 않는다."""

    model_config = ConfigDict(extra="ignore", allow_inf_nan=False)

    move_count: int = Field(default=0, ge=0, le=_MAX_COUNT)
    path_px: float = Field(default=0, ge=0, le=_MAX_PX)
    straightness: float = Field(default=0, ge=0, le=1)
    click_count: int = Field(default=0, ge=0, le=_MAX_COUNT)
    click_iv_mean: float = Field(default=0, ge=0, le=_MAX_MS)
    click_iv_std: float = Field(default=0, ge=0, le=_MAX_MS)
    key_count: int = Field(default=0, ge=0, le=_MAX_COUNT)
    key_iv_std: float = Field(default=0, ge=0, le=_MAX_MS)
    dwell_ms: float = Field(default=0, ge=0, le=_MAX_MS)
    touch_count: int = Field(default=0, ge=0, le=_MAX_COUNT)  # touchstart·touchmove 수
    kbd_click_count: int = Field(default=0, ge=0, le=_MAX_COUNT)  # 키보드가 만든 클릭 수

    @model_validator(mode="after")
    def _kbd_clicks_within_clicks(self) -> SignalsSchema:
        if self.kbd_click_count > self.click_count:
            raise ValueError("kbd_click_count must not exceed click_count")
        return self


class ScoreRequestSchema(_PublicRequest):
    site_key: str = Field(..., max_length=64, description="공개 키(pk_, SDK에 박힘)")
    signals: SignalsSchema = Field(default_factory=lambda: SignalsSchema())


class ScoreResponseSchema(BaseModel):
    token: str = Field(..., description="서명 토큰 — 고객 서버가 /verify로 확인한다")
    verdict: Literal["allow", "challenge", "block"] = Field(..., description="브라우저용 참고값")


class VerifyRequestSchema(_PublicRequest):
    secret: str = Field(..., max_length=128, description="고객 서버만 아는 비밀 키(sk_)")
    token: str = Field(..., max_length=4096, description="/score가 내려준 토큰")


class ScoreResultSchema(BaseModel):
    score: float
    verdict: Literal["allow", "challenge", "block"]
    rule_score: float
    model_score: float | None
    decided_by: Literal["rule", "model"]
    reasons: list[str]
