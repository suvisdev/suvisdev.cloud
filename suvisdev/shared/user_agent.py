"""User-Agent 봇 판정 — 앱 공용(2026-10-07 analytics에서 이동, mova 열람 랭킹도 쓴다).

스포크끼리는 서로 import할 수 없어(스타 토폴로지) 두 앱이 같은 규칙을 쓰려면 여기 둔다.
"""

from __future__ import annotations

import re

# 크롤러·링크 미리보기·헤드리스 브라우저·CLI. UA가 없어도 봇(브라우저는 항상 보낸다).
_BOT_UA = re.compile(
    r"bot|crawl|spider|slurp|headless|phantom|puppeteer|playwright|selenium|lighthouse|"
    r"preview|scrap|fetch|curl|wget|python-requests|httpx|go-http-client|java/|"
    r"inspectiontool|facebookexternalhit|kakaotalk|twitterbot|discordbot|slackbot|whatsapp|"
    r"telegrambot|yeti|daum|bingbot|baiduspider|yandex|duckduck|petalbot|semrush|ahrefs|mj12|dotbot",
    re.IGNORECASE,
)


def is_bot_user_agent(user_agent: str | None) -> bool:
    ua = (user_agent or "").strip()
    return not ua or bool(_BOT_UA.search(ua))
