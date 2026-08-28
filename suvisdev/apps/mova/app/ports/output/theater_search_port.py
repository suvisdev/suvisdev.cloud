"""영화관 검색 출력 포트 — booking 트랙(예매 보조) 전용."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.market_chat_dto import ChatTheaterDto


class TheaterSearchPort(ABC):
    @abstractmethod
    async def search_theaters(self, region: str, *, limit: int = 5) -> list[ChatTheaterDto] | None:
        """지역명 → 근처 영화관 목록(가까운 순).

        None = 지역명을 좌표로 해석하지 못했거나 검색 자체가 실패(키 미설정·
        외부 API 오류 포함) — 호출자는 다른 지역명으로 다시 물어보게 안내한다.
        [] = 지역은 찾았지만 근처에 영화관이 없음.
        """
