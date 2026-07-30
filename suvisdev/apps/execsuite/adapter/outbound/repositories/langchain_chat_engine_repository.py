"""LangChain으로 구현한 챗봇 엔진 — LangchainChatEnginePort 구현체.

semantic_router_interactor(ontology)가 판단한 destination·entities·grounding을
시스템 프롬프트에 반영해, 같은 대화 맥락(history)을 두고 최종 답변을 생성한다.
Gemini(langchain-google-genai)를 호출한다 — API 키는 core.matrix의 Keymaker를
그대로 재사용해 ontology GeminiLlmAdapter 등 다른 Gemini 사용처와 키 관리를
일원화한다.
"""

from __future__ import annotations

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI

from core.matrix.vauly_keymaker_secret_manager import GEMINI_MODEL_MAP, get_keymaker
from execsuite.app.ports.output.langchain_chat_errors import LangchainChatError

_MODEL = GEMINI_MODEL_MAP["flash15"]

_BASE_PROMPT = (
    "너는 SUVIS의 한국어 어시스턴트야. 반드시 한국어로, 간결하게 답해.\n"
    "추측하지 말고, 주어진 정보 안에서만 답해."
)


def _build_system_prompt(destination: str, entities: str, grounding: str) -> str:
    """destination(semantic_router 판단)별로 다른 시스템 프롬프트를 만든다.

    grounding·entities는 완성된 문자열 하나로 만든 뒤 "{system_prompt}" 자리에
    값으로만 주입한다 — grounding 안에 "{"·"}"가 섞여 있어도 LangChain의 템플릿
    파서가 재해석하지 않도록 하기 위함이다.
    """
    if destination == "rag":
        return (
            f"{_BASE_PROMPT}\n\n"
            "아래 [참고자료]에 있는 내용만 근거로 답해. "
            "없는 내용은 '제공된 자료에 없습니다'라고 말해. 지어내지 마.\n\n"
            f"[참고자료]\n{grounding}\n\n"
            f"[엔티티] {entities}"
        )
    if destination == "crud":
        return f"{_BASE_PROMPT}\n\n요청 작업 의도를 확인하는 문장만 생성해. 실제 실행은 하지 마.\n[대상] {entities}"
    return f"{_BASE_PROMPT}\n\n사용자와 자연스럽게 대화해."


def _to_langchain_messages(messages: list[dict[str, str]]) -> list[BaseMessage]:
    return [
        HumanMessage(content=m.get("content", ""))
        if m.get("role") == "user"
        else AIMessage(content=m.get("content", ""))
        for m in messages
    ]


class LangchainChatEngineRepository:
    def __init__(self, model: str = _MODEL) -> None:
        llm = ChatGoogleGenerativeAI(model=model, google_api_key=get_keymaker().gemini_api_key)
        prompt = ChatPromptTemplate.from_messages(
            [("system", "{system_prompt}"), MessagesPlaceholder("history")]
        )
        self._chain = prompt | llm | StrOutputParser()

    async def generate(
        self,
        *,
        messages: list[dict[str, str]],
        destination: str,
        entities: list[str],
        grounding: str,
    ) -> str:
        system_prompt = _build_system_prompt(
            destination, ", ".join(entities) or "없음", grounding or "없음"
        )
        try:
            return await self._chain.ainvoke(
                {"system_prompt": system_prompt, "history": _to_langchain_messages(messages)}
            )
        except Exception as e:
            raise LangchainChatError(f"LangChain 챗봇 엔진 호출 실패: {e}") from e
