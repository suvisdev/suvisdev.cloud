"""스팸 분류 택소노미 — 카테고리별 설명 및 LLM 프롬프트 빌더."""

from __future__ import annotations

from ontology.domain.spam.spam_category import SpamCategory

CATEGORY_DESCRIPTIONS: dict[SpamCategory, str] = {
    SpamCategory.ADVERTISING: "상업적 광고·프로모션 메일",
    SpamCategory.PHISHING: "개인정보·계정 탈취 시도",
    SpamCategory.MALWARE: "악성 링크·첨부파일 포함",
    SpamCategory.BULK: "무분별 대량 발송 메일",
    SpamCategory.SCAM: "금전 사기·투자 유인 시도",
    SpamCategory.HAM: "스팸이 아닌 정상 메일",
}


def build_classifier_system_prompt() -> str:
    """LLM 분류 시스템 프롬프트를 택소노미 기반으로 생성한다."""
    category_lines = "\n".join(
        f"- {cat.value}: {desc}" for cat, desc in CATEGORY_DESCRIPTIONS.items()
    )
    return (
        "당신은 스팸 메일 분류 전문가입니다.\n"
        f"다음 카테고리 중 하나를 선택하여 메일을 분류하세요:\n{category_lines}\n\n"
        "반드시 다음 형식으로만 답하세요:\n"
        "카테고리: [카테고리명]\n"
        "이유: [한 줄 이유]"
    )
