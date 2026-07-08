from __future__ import annotations

from core.lol.t1_mid_faker_orchestrator import FakerOrchestratorError, T1MidFakerOrchestrator
from ontology.domain.spam.spam_category import SpamCategory
from ontology.domain.spam.spam_rules import quick_filter
from ontology.domain.spam.spam_taxonomy import build_classifier_system_prompt
from spam_filter.app.dtos.spam_dto import SpamClassifyDto
from spam_filter.app.ports.output.spam_errors import SpamFilterError

_SYSTEM_PROMPT = build_classifier_system_prompt()


def _build_user_prompt(*, subject: str, body: str, sender: str | None) -> str:
    lines = [f"제목: {subject}", f"본문: {body[:1000]}"]
    if sender:
        lines.insert(0, f"발신자: {sender}")
    return "\n".join(lines)


def _parse_llm_response(raw: str) -> SpamClassifyDto:
    category = SpamCategory.HAM
    reason = raw[:200]

    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("카테고리:"):
            candidate = stripped.split(":", 1)[1].strip()
            try:
                category = SpamCategory(candidate)
            except ValueError:
                pass
        elif stripped.startswith("이유:"):
            reason = stripped.split(":", 1)[1].strip()

    return SpamClassifyDto(
        category=category.value,
        is_spam=category.is_spam,
        reason=reason,
    )


class SpamClassifyInteractor:
    def __init__(self, *, orchestrator: T1MidFakerOrchestrator) -> None:
        self._orchestrator = orchestrator

    def classify(self, *, subject: str, body: str, sender: str | None) -> SpamClassifyDto:
        # 사전 필터: 키워드 일치 시 LLM 생략
        quick = quick_filter(subject=subject, body=body)
        if quick is not None:
            return SpamClassifyDto(
                category=quick.value,
                is_spam=quick.is_spam,
                reason="키워드 규칙 매칭",
            )

        prompt = _build_user_prompt(subject=subject, body=body, sender=sender)
        try:
            raw = self._orchestrator.generate(prompt, system=_SYSTEM_PROMPT)
        except FakerOrchestratorError as e:
            raise SpamFilterError(f"LLM 분류 실패: {e.detail}", status_code=e.status_code) from e

        return _parse_llm_response(raw)
