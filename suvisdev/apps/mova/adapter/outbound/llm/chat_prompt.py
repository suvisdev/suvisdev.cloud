import logging
from typing import Any

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
- 사용자가 장르·분위기·배우·OTT 등 **영화 관련 의도**를 표현한 경우에만 영화를 추천하세요.
- 인사(안녕, 안녕하세요, hi 등), 단순 잡담, 의도가 불분명한 메시지에는 추천하지 말고 어떤 영화를 찾는지 먼저 질문하세요.
- intro는 1~2문장으로 짧게 (인사·취향 요약 또는 추가 질문).
- **추천은 반드시 아래 [태그·DB 카탈로그]에 있는 작품 중에서만 하세요 — 카탈로그에
  없는 영화는 절대 추천하지 마세요.** 실제로 존재하지 않거나 동명의 다른 작품과
  착각해 잘못 추천할 위험이 있습니다.
- 각 pick에는 그 작품의 movie_id(카탈로그에 적힌 정수)를 그대로 포함하세요. title은
  그 movie_id에 해당하는 제목을 그대로 쓰세요.
- 카탈로그에 조건에 맞는 작품이 3편 미만이면 있는 만큼만(0~2편) 추천하고, intro에서
  그 사실을 짧게 안내하세요. 억지로 3편을 채우지 마세요.
- [태그·DB 카탈로그]가 비어 있으면 picks를 빈 배열로 두고, intro에서 조건에 맞는
  작품을 카탈로그에서 찾지 못했다고 안내하세요.
- hook은 한 줄 추천 이유(40자 이내).
- JSON만 출력, 다른 텍스트 금지.
- 모든 텍스트는 순수 한글로만 쓰세요. 한자(漢字)를 절대 섞지 마세요 — 예를 들어
  "作品"이 아니라 "작품", "感情"이 아니라 "감정"처럼 반드시 한글로 표기하세요.

출력 형식:
{{"intro": "짧은 소개 문장 또는 질문", "picks": [{{"movie_id": 123, "title": "영화 제목", "hook": "한 줄 이유"}}, ...]}}

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
        search_filters: dict[str, Any] | None = None,
    ) -> str:
        if not refined_query and not keywords:
            return ""
        kw = ", ".join(keywords) if keywords else "(없음)"
        filters = search_filters if isinstance(search_filters, dict) else {}
        _must_val = filters.get("must")
        must: dict[str, Any] = _must_val if isinstance(_must_val, dict) else {}
        _sim_val = filters.get("similar_to")
        similar: dict[str, Any] = _sim_val if isinstance(_sim_val, dict) else {}
        and_parts: list[str] = []
        for actor in must.get("actors") or []:
            and_parts.append(f"배우={actor}")
        for genre in must.get("genres") or []:
            and_parts.append(f"장르={genre}")
        for tag_kw in must.get("keywords") or []:
            and_parts.append(f"태그={tag_kw}")
        # RAG(semantic) 경로는 연도 하드 필터를 SQL로 못 거니 LLM에게라도 알린다
        # — "클래식" 요청에 최신작이 후보로 와도 LLM이 연도로 거를 수 있게.
        year_min, year_max = filters.get("year_min"), filters.get("year_max")
        if year_min is not None or year_max is not None:
            and_parts.append(f"연도={year_min or ''}~{year_max or ''}")
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
            "반드시 이 목록의 movie_id 중에서만 골라 추천하세요(목록에 없는 영화 추천 금지).",
        ]
        # 조건 매칭이 전부 실패해 인기작 폴백으로만 채워진 후보를 "엄선했다"고
        # 포장하면 안 된다(2026-08-28 정직 문구 규칙 — .claude/rules/mova-chat.md §4).
        if all(item.match_type == "popular_fallback" for item in hits):
            lines.append(
                "주의: 이 목록은 요청 조건과 매칭된 결과가 아니라, 조건에 맞는 작품을 "
                "찾지 못해 인기작에서 고른 폴백 후보입니다. intro에서 '엄선했다'·"
                "'조건에 맞춰 골랐다'처럼 말하지 말고, '조건에 딱 맞는 작품은 못 찾아 "
                "인기작 중에서 골라봤다'고 정직하게 밝히세요."
            )
        for item in hits[:12]:
            kind = "태그" if item.match_type == "keyword" else item.match_type
            # 제목·연도만 주면 LLM이 작품 내용을 모른 채 제목으로 추측한다 —
            # "형사물"에 무관한 작품을 고르거나 줄거리를 지어내는 실패의 원인이었다
            # (2026-09-22, v3 평가 패배 25건 중 최다 사유). 장르·한 줄 요약을 함께 준다.
            parts = [f"- movie_id={item.id} {item.title} ({item.year or '연도 미상'})"]
            if item.genres:
                parts.append(f"[{item.genres}]")
            parts.append(f"[{kind}]")
            if item.summary:
                # 구분자 없이 이어 붙이면 LLM이 줄거리까지 제목으로 읽는다
                # (2026-09-22 실측: title에 줄거리가 통째로 들어간 응답). "줄거리:"로
                # 경계를 분명히 한다.
                parts.append(f"— 줄거리: {item.summary}")
            lines.append(" ".join(parts))
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
        search_filters: dict[str, Any] | None = None,
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

    def parse_structured_reply(self, raw: str) -> tuple[str, list[Any]]:
        return self.reply_service.parse_gemini_reply(raw)
