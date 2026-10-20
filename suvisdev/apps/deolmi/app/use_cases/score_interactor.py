from __future__ import annotations

import asyncio
import logging

from deolmi.app.dtos.score_dto import IssuedScoreDto, ScoreCommand, ScoreResultDto, VerifyCommand
from deolmi.app.errors import BadSecretError, OriginNotAllowedError, UnknownSiteError
from deolmi.app.ports.input.score_use_case import ScoreUseCase
from deolmi.app.ports.output.anomaly_model_port import AnomalyModelPort
from deolmi.app.ports.output.event_repository import EventRepositoryPort
from deolmi.app.ports.output.score_token_port import ScoreTokenPort
from deolmi.app.ports.output.site_repository import SiteRepositoryPort
from deolmi.app.ports.output.velocity_port import VelocityPort
from deolmi.domain.services.origin_policy import origin_allowed
from deolmi.domain.services.scoring_policy import (
    BLOCK_THRESHOLD,
    rule_score,
    to_features,
    verdict_of,
)
from deolmi.domain.services.site_keys import secret_matches

logger = logging.getLogger(__name__)


class ScoreInteractor(ScoreUseCase):
    """채점(/score)과 검증(/verify).

    폭주 대응(cheap_first): 규칙만으로 이미 차단 수준이면 모델을 건너뛴다 — 티켓 오픈처럼
    요청이 쏟아질 때 비용을 아끼는 장치. 최종 점수는 max(규칙, 모델).
    """

    def __init__(
        self,
        sites: SiteRepositoryPort,
        events: EventRepositoryPort,
        model: AnomalyModelPort,
        tokens: ScoreTokenPort,
        velocity: VelocityPort,
    ) -> None:
        self._sites = sites
        self._events = events
        self._model = model
        self._tokens = tokens
        self._velocity = velocity

    async def score(self, command: ScoreCommand) -> IssuedScoreDto:
        site = await self._sites.get_active(command.site_key)
        if site is None:
            raise UnknownSiteError(command.site_key)
        if not origin_allowed(command.origin, site.domains):
            raise OriginNotAllowedError(command.origin or "")

        velocity = self._velocity.record(f"{site.site_key}:{command.client_ip}")
        result = await self._evaluate(command.signals, velocity)

        # 로그는 재학습 원천이지만, 저장 실패가 채점 응답을 막으면 안 된다.
        try:
            await self._events.add(site.id, command.client_ip, command.signals, result)
        except Exception:
            logger.exception("[deolmi] 이벤트 저장 실패 — 응답은 그대로 보낸다")

        token = self._tokens.issue(site.site_key, result.to_dict())
        return IssuedScoreDto(token=token, verdict=result.verdict)

    async def verify(self, command: VerifyCommand) -> ScoreResultDto:
        payload = self._tokens.decode(command.token)
        site = await self._sites.get_active(payload.site_key)
        if site is None or not secret_matches(command.secret, site.secret_hash):
            raise BadSecretError
        # 비밀 키가 맞을 때만 소모한다 — 틀린 키로 남의 토큰을 태워 버리지 못하게.
        self._tokens.consume(payload)
        return ScoreResultDto.from_dict(payload.result)

    async def _evaluate(self, signals: dict[str, float], velocity: int) -> ScoreResultDto:
        rule = rule_score(signals, velocity)
        if rule.score >= BLOCK_THRESHOLD:
            model_score = None
            final = rule.score
            decided_by = "rule"
        else:
            # IsolationForest 추론은 CPU 연산 — 이벤트 루프를 막지 않게 스레드로 넘긴다.
            raw = await asyncio.to_thread(self._model.score, to_features(signals))
            model_score = round(raw, 3)
            final = max(rule.score, model_score)
            decided_by = "rule" if rule.score >= model_score else "model"
        return ScoreResultDto(
            score=round(final, 3),
            verdict=verdict_of(final),
            rule_score=round(rule.score, 3),
            model_score=model_score,
            decided_by=decided_by,
            reasons=list(rule.reasons),
        )
