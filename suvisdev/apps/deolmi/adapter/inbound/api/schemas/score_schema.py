from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SignalsSchema(BaseModel):
    """SDK가 모으는 행동 신호. 입력 글자는 없다 — 리듬·궤적 수치만.
    모르는 키는 버린다(로그에 임의 값이 쌓이지 않게)."""

    model_config = ConfigDict(extra="ignore")

    move_count: int = Field(default=0, ge=0)
    path_px: float = Field(default=0, ge=0)
    straightness: float = Field(default=0, ge=0, le=1)
    click_count: int = Field(default=0, ge=0)
    click_iv_mean: float = Field(default=0, ge=0)
    click_iv_std: float = Field(default=0, ge=0)
    key_count: int = Field(default=0, ge=0)
    key_iv_std: float = Field(default=0, ge=0)
    dwell_ms: float = Field(default=0, ge=0)


class ScoreRequestSchema(BaseModel):
    site_key: str = Field(..., max_length=64, description="공개 키(pk_, SDK에 박힘)")
    signals: SignalsSchema = Field(default_factory=lambda: SignalsSchema())


class ScoreResponseSchema(BaseModel):
    token: str = Field(..., description="서명 토큰 — 고객 서버가 /verify로 확인한다")
    verdict: Literal["allow", "challenge", "block"] = Field(..., description="브라우저용 참고값")


class VerifyRequestSchema(BaseModel):
    secret: str = Field(..., max_length=128, description="고객 서버만 아는 비밀 키(sk_)")
    token: str = Field(..., max_length=4096, description="/score가 내려준 토큰")


class ScoreResultSchema(BaseModel):
    score: float
    verdict: Literal["allow", "challenge", "block"]
    rule_score: float
    model_score: float | None
    decided_by: Literal["rule", "model"]
    reasons: list[str]
