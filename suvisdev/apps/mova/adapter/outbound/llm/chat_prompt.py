import logging

from mova.adapter.inbound.api.schemas.studio_search_schema import MovaSearchItemSchema
from mova.adapter.outbound.llm.chat_reply import ChatReplyService
from mova.adapter.outbound.llm.llm_safety import (
    INJECTION_GUARD,
    fence_user_text,
    sanitize_user_text,
)
from mova.adapter.outbound.orm.market_chat_orm import MovaChat

logger = logging.getLogger(__name__)

MOVA_SYSTEM_PROMPT = """당신은 영화·시리즈 추천 AI 'Mova'입니다.

규칙:
- 사용자가 장르·분위기·배우·OTT 등 **영화 관련 의도**를 표현한 경우에만 영화 3편을 추천하세요.
- 인사(안녕, 안녕하세요, hi 등), 단순 잡담, 의도가 불분명한 메시지에는 추천하지 말고 어떤 영화를 찾는지 먼저 질문하세요.
- intro는 1~2문장으로 짧게 (인사·취향 요약 또는 추가 질문).
- 추천할 때 picks는 정확히 3개, 각 항목에 영화 제목(title)과 hook(한 줄 추천 이유, 40자 이내).
- 추천하지 않을 때는 picks를 빈 배열로 두세요.
- [태그·DB 카탈로그]에 작품이 있으면 그 목록에서 우선 골라 추천하세요 (tags 테이블 매칭).
- JSON만 출력, 다른 텍스트 금지.

출력 형식:
{{"intro": "짧은 소개 문장 또는 질문", "picks": [{{"title": "영화 제목", "hook": "한 줄 이유"}}, ...]}}

{intent_section}
{tag_catalog_section}
{past_intents_section}
{user_preferences_section}
"""


class ChatPromptBuilder:
    def __init__(self) -> None:
        self.reply_service = ChatReplyService()

    def format_intent_section(
        self,
        refined_query: str,
        keywords: list[str],
        *,
        intent_type: str = "mood",
        search_filters: dict | None = None,
    ) -> str:
        if not refined_query and not keywords:
            return ""
        kw = ", ".join(keywords) if keywords else "(없음)"
        filters = search_filters if isinstance(search_filters, dict) else {}
        must = filters.get("must") if isinstance(filters.get("must"), dict) else {}
        similar = filters.get("similar_to") if isinstance(filters.get("similar_to"), dict) else {}
        and_parts: list[str] = []
        for actor in must.get("actors") or []:
            and_parts.append(f"배우={actor}")
        for genre in must.get("genres") or []:
            and_parts.append(f"장르={genre}")
        for tag_kw in must.get("keywords") or []:
            and_parts.append(f"태그={tag_kw}")
        and_line = " AND ".join(and_parts) if and_parts else "(없음)"
        anchor = ", ".join(similar.get("actors") or []) or "(없음)"
        return (
            f"\n[이번 질문 검색 의도]\n"
            f"분류: {intent_type} | 정제: {refined_query} | 키워드: {kw}\n"
            f"AND 조건(must): {and_line} | 유사 기준(similar_to): {anchor}\n"
        )

    def format_user_preferences_section(
        self,
        nickname: str | None,
        preferred_genres: list[str] | None,
    ) -> str:
        genres = [g.strip() for g in (preferred_genres or []) if str(g).strip()]
        if not genres:
            return ""
        name = (nickname or "회원").strip()
        joined = ", ".join(genres)
        return f"\n[사용자 취향 프로필 — {name}]\n선호 장르: {joined}\n위 장르를 우선 반영해 추천하세요.\n"

    def format_tag_catalog_section(self, hits: list[MovaSearchItemSchema]) -> str:
        if not hits:
            return ""
        lines = [
            "\n[태그·DB 카탈로그 — 의도 키워드로 조회된 작품]",
            "아래는 `tags`·제목·장르 등 DB 검색 결과입니다. 가능하면 picks 3편을 여기서 고르세요.",
        ]
        for item in hits[:12]:
            kind = "태그" if item.match_type == "keyword" else item.match_type
            lines.append(f"- {item.title} ({item.year or '연도 미상'}) [{kind}]")
        return "\n".join(lines)

    def format_past_intents_section(self, intents: list[MovaChat]) -> str:
        if not intents:
            return ""
        lines = ["\n[자주 찾았던 취향]"]
        for item in intents:
            lines.append(f"- {item.refined_query}")
        return "\n".join(lines)

    def build_prompt(
        self,
        history: list[dict[str, str]],
        message: str,
        *,
        refined_query: str = "",
        keywords: list[str] | None = None,
        intent_type: str = "mood",
        search_filters: dict | None = None,
        past_intents: list[MovaChat] | None = None,
        tag_catalog: list[MovaSearchItemSchema] | None = None,
        user_nickname: str | None = None,
        preferred_genres: list[str] | None = None,
    ) -> str:
        parts = [
            MOVA_SYSTEM_PROMPT.format(
                intent_section=self.format_intent_section(
                    refined_query,
                    keywords or [],
                    intent_type=intent_type,
                    search_filters=search_filters,
                ),
                tag_catalog_section=self.format_tag_catalog_section(tag_catalog or []),
                past_intents_section=self.format_past_intents_section(past_intents or []),
                user_preferences_section=self.format_user_preferences_section(
                    user_nickname,
                    preferred_genres,
                ),
            ),
            "",
            INJECTION_GUARD,
            "",
            "[대화]",
        ]
        # history 도 클라이언트 제공값 → 정화
        for item in history[-6:]:
            role = item.get("role", "user")
            label = "사용자" if role == "user" else "Mova"
            parts.append(f"{label}: {sanitize_user_text(str(item.get('content', '')))}")
        # 이번 사용자 입력은 데이터 구분자로 감싼다
        parts.append(f"사용자: {fence_user_text(message)}")
        parts.append("JSON:")
        return "\n".join(parts)

    def parse_structured_reply(self, raw: str):
        return self.reply_service.parse_gemini_reply(raw)
