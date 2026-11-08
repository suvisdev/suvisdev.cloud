"""'오늘의 핫한 소식' 규칙 (외부 의존 없음, 2026-11-06).

화제 정도는 모델이 판단하지 않고 사람들의 반응 수치로 정한다 — 논문은 Hugging Face Daily Papers 추천 수,
커뮤니티 글은 Hacker News 점수. 두 숫자는 단위가 달라 합치지 않고 출처별로 순위를 매긴다.
Hacker News 는 AI 글만 다루지 않아 제목으로 거른다.
"""

from __future__ import annotations

import re

HOT_PAPERS = "hf"
HOT_COMMUNITY = "hn"
HOT_WINDOW_HOURS = 12  # 이 시간 안에 수치가 갱신된 글만 보여 준다 — 수집은 30분마다, 노트북이 꺼져 있어도 한나절은 유지

_AI_TITLE = re.compile(
    r"\b(?:AI|AGI|LLM|LLMs|GPT|GPT-?\d[\w.]*|ChatGPT|Claude|Gemini|Copilot|Grok|OpenAI|Anthropic|DeepMind"
    r"|DeepSeek|Qwen|Kimi|Mistral|Llama|Ollama|vLLM|Hugging ?Face|Transformers?|RAG|MCP|NVIDIA|Nvidia|CUDA"
    r"|[Aa]gents?|[Aa]gentic|[Nn]eural|[Ii]nference|[Mm]achine [Ll]earning|[Dd]eep [Ll]earning"
    r"|[Ll]anguage [Mm]odels?|[Mm]odel [Ww]eights|[Oo]pen [Ww]eights)\b"
)


def is_ai_title(title: str) -> bool:
    return bool(_AI_TITLE.search(title))


def papers_label(upvotes: int) -> str:
    return f"추천 {upvotes:,}"


def community_label(points: int, comments: int) -> str:
    return f"{points:,}점 · 댓글 {comments:,}"
