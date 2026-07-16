"""임의 페이지 + 자연어 지시 → 추출 결과 — PageExtractorPort 구현체.

로컬 Qwen(1.5B)은 컨텍스트가 좁아서 페이지 전체 본문을 넣기엔 부족하다 — 이미
QwenLlmAdapter의 용도(라우팅·짧은 RAG 답변)와도 다르므로, 더 큰 컨텍스트를 감당할
수 있는 Gemini(GeminiLlmAdapter)를 재사용한다.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from ontology.app.dtos.custom_scrape_dto import ExtractedPage
from ontology.app.ports.output.hub_llm_port import HubLlmPort
from ontology.app.ports.output.page_extractor_port import PageExtractorPort

_MAX_PAGE_CHARS = 15_000

_SYSTEM_PROMPT = (
    "너는 웹페이지에서 사용자가 지시한 정보만 뽑아내는 도우미야. "
    "아래 페이지 본문에서 지시사항에 맞는 내용만 골라 간결한 텍스트로 답해. "
    "지시와 무관한 설명·인사말·페이지 전체 재진술은 하지 마. "
    "지시에 맞는 내용이 페이지에 없으면 '해당 정보를 페이지에서 찾지 못했습니다'라고만 답해."
)


class GeminiPageExtractorAdapter(PageExtractorPort):
    def __init__(self, *, llm: HubLlmPort) -> None:
        self._llm = llm

    async def extract(self, html: str, instruction: str) -> ExtractedPage:
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else ""
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)[:_MAX_PAGE_CHARS]

        prompt = f"지시사항: {instruction}\n\n페이지 본문:\n{text}"
        content = await self._llm.generate(prompt, system=_SYSTEM_PROMPT)
        return ExtractedPage(title=title or instruction[:80], content=content.strip())
