"""TheaterSearchPort 구현 — 카카오 로컬 API(booking 트랙 전용).

gildle 지오코딩과 같은 `KAKAO_API_KEY`(REST API 키)를 쓰지만, 스포크 간 직접
import 금지 규칙에 따라 mova 안에 자체 어댑터를 둔다. 검색 실패는 전부
None으로 수렴시킨다 — 예매 보조가 죽어도 채팅 자체는 계속 동작해야 한다.
"""

from __future__ import annotations

import logging

import httpx

from mova.app.dtos.market_chat_dto import ChatTheaterDto
from mova.app.ports.output.theater_search_port import TheaterSearchPort

logger = logging.getLogger(__name__)

_KAKAO_BASE = "https://dapi.kakao.com"
_ADDRESS_PATH = "/v2/local/search/address.json"
_KEYWORD_PATH = "/v2/local/search/keyword.json"
_TIMEOUT_S = 10.0


class KakaoLocalTheaterAdapter(TheaterSearchPort):
    def __init__(self, api_key: str) -> None:
        self._api_key = (api_key or "").strip()

    async def search_theaters(
        self, region: str, *, limit: int = 5, radius_m: int = 10_000
    ) -> list[ChatTheaterDto] | None:
        region = (region or "").strip()
        if not region:
            return None
        if not self._api_key:
            logger.warning("[KakaoLocalTheaterAdapter] KAKAO_API_KEY 미설정 — 영화관 검색 생략")
            return None

        headers = {"Authorization": f"KakaoAK {self._api_key}"}
        try:
            async with httpx.AsyncClient(
                base_url=_KAKAO_BASE, headers=headers, timeout=_TIMEOUT_S
            ) as client:
                coords = await self._resolve_coords(client, region)
                if coords is None:
                    return None
                x, y = coords
                res = await client.get(
                    _KEYWORD_PATH,
                    params={
                        "query": "영화관",
                        "x": x,
                        "y": y,
                        "radius": radius_m,
                        "sort": "distance",
                        "size": min(limit, 15),
                    },
                )
                res.raise_for_status()
                documents = res.json().get("documents") or []
        except httpx.HTTPError as e:
            logger.warning("[KakaoLocalTheaterAdapter] 검색 실패 region=%s | %s", region, e)
            return None

        theaters = [
            ChatTheaterDto(
                name=str(doc.get("place_name") or ""),
                address=str(doc.get("road_address_name") or doc.get("address_name") or ""),
                distance_m=int(d) if (d := str(doc.get("distance") or "")).isdigit() else None,
                place_url=str(doc.get("place_url") or ""),
                phone=str(doc.get("phone") or ""),
                lat=float(doc["y"]) if doc.get("y") else None,
                lng=float(doc["x"]) if doc.get("x") else None,
            )
            for doc in documents
            if doc.get("place_name")
        ]
        logger.info("[KakaoLocalTheaterAdapter] region=%s theaters=%d", region, len(theaters))
        return theaters

    async def _resolve_coords(
        self, client: httpx.AsyncClient, region: str
    ) -> tuple[str, str] | None:
        """지역명 → (x, y). 주소 검색 실패 시 키워드 검색(역·랜드마크 대응)으로 폴백."""
        for path in (_ADDRESS_PATH, _KEYWORD_PATH):
            res = await client.get(path, params={"query": region, "size": 1})
            res.raise_for_status()
            documents = res.json().get("documents") or []
            if documents and documents[0].get("x") and documents[0].get("y"):
                return str(documents[0]["x"]), str(documents[0]["y"])
        return None
