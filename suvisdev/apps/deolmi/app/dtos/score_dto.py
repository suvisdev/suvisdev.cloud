from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from deolmi.domain.services.scoring_policy import Verdict

if TYPE_CHECKING:
    from deolmi.adapter.inbound.api.schemas.score_schema import (
        ScoreRequestSchema,
        ScoreResponseSchema,
        ScoreResultSchema,
        VerifyRequestSchema,
    )


@dataclass(frozen=True)
class ScoreCommand:
    site_key: str
    signals: dict[str, float]
    origin: str | None
    client_ip: str

    @classmethod
    def from_schema(
        cls, schema: ScoreRequestSchema, origin: str | None, client_ip: str
    ) -> ScoreCommand:
        return cls(
            site_key=schema.site_key,
            signals=schema.signals.model_dump(),
            origin=origin,
            client_ip=client_ip,
        )


@dataclass(frozen=True)
class VerifyCommand:
    secret: str
    token: str

    @classmethod
    def from_schema(cls, schema: VerifyRequestSchema) -> VerifyCommand:
        return cls(secret=schema.secret, token=schema.token)


@dataclass(frozen=True)
class ScoreResultDto:
    score: float
    verdict: Verdict
    rule_score: float
    model_score: float | None  # None이면 규칙만으로 차단 수준이라 모델을 생략함(폭주 대응)
    decided_by: str
    reasons: list[str]  # 왜 의심하는지 — 이의 제기 대응과 디버깅용

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ScoreResultDto:
        return cls(**d)

    def to_schema(self) -> ScoreResultSchema:
        from deolmi.adapter.inbound.api.schemas.score_schema import ScoreResultSchema

        return ScoreResultSchema(**self.to_dict())


@dataclass(frozen=True)
class IssuedScoreDto:
    token: str
    verdict: Verdict  # 브라우저용 참고값 — 실제 판단은 고객 서버가 /verify로 한다

    def to_schema(self) -> ScoreResponseSchema:
        from deolmi.adapter.inbound.api.schemas.score_schema import ScoreResponseSchema

        return ScoreResponseSchema(token=self.token, verdict=self.verdict)


@dataclass(frozen=True)
class ScoreTokenPayload:
    jti: str
    site_key: str
    expires_at: float
    result: dict[str, Any]
