"""PetPlacePort 구현 — 카카오 로컬 키워드 검색으로 반려동물 장소를 찾는다(2026-09-28).

키워드 4개(동물병원·애견용품·펫샵·애견카페)를 중심 좌표 반경으로 검색하고 place_id로 중복을 뺀다.
같은 중심·반경은 10분 캐시(후보 계산마다 호출). 키가 없거나 실패하면 [] — 경로는 장소 없이도 나간다.
mova에도 카카오 어댑터가 있지만 스포크 간 import 금지라 gildle 전용으로 둔다(같은 KAKAO_API_KEY).
"""

from __future__ import annotations

import logging
import os
import time

import httpx

from gildle.app.ports.output.pet_place_port import PetPlacePort
from gildle.domain.value_objects.coordinate import Coordinate
from gildle.domain.value_objects.pet_place import PetPlace

logger = logging.getLogger(__name__)

_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
_TIMEOUT_S = 5.0
_CACHE_TTL_S = 600
_KEYWORDS = (
    ("동물병원", "동물병원"),
    ("애견용품", "용품점"),
    ("펫샵", "펫샵"),
    ("애견카페", "애견카페"),
)


def _category(doc: dict, fallback: str) -> str:
    """카카오 category_name("가정,생활 > 반려동물 > 동물병원")에서 우리 분류로."""
    name = f"{doc.get('category_name', '')} {doc.get('place_name', '')}"
    if "동물병원" in name or "동물의료" in name:
        return "동물병원"
    if "카페" in name:
        return "애견카페"
    if "용품" in name:
        return "용품점"
    if "분양" in name or "펫샵" in name or "애견샵" in name:
        return "펫샵"
    return fallback


class KakaoPetPlaceAdapter(PetPlacePort):
    def __init__(self, api_key: str | None = None) -> None:
        self._key = api_key if api_key is not None else os.getenv("KAKAO_API_KEY", "")
        self._cache: dict[tuple[float, float, int], tuple[float, list[PetPlace]]] = {}

    def search_around(self, center: Coordinate, radius_m: int) -> list[PetPlace]:
        if not self._key:
            return []
        key = (round(center.latitude, 3), round(center.longitude, 3), radius_m // 100)
        hit = self._cache.get(key)
        if hit and time.monotonic() - hit[0] < _CACHE_TTL_S:
            return hit[1]
        found: dict[str, PetPlace] = {}
        try:
            with httpx.Client(
                timeout=_TIMEOUT_S, headers={"Authorization": f"KakaoAK {self._key}"}
            ) as client:
                for query, fallback in _KEYWORDS:
                    res = client.get(
                        _URL,
                        params={
                            "query": query,
                            "x": center.longitude,
                            "y": center.latitude,
                            "radius": min(20_000, max(1, radius_m)),
                            "sort": "distance",
                            "size": 15,
                        },
                    )
                    res.raise_for_status()
                    for doc in res.json().get("documents") or []:
                        pid = str(doc.get("id") or "")
                        if not pid or pid in found or not doc.get("x") or not doc.get("y"):
                            continue
                        # 반려동물과 무관한 검색 잡음(강아지떡볶이 같은 식당)을 거른다 — 검색어 기본 분류를
                        # 믿으면 "동물병원" 검색에 걸린 식당이 동물병원으로 통과한다(09-28 테스트로 발견).
                        cat_text = str(doc.get("category_name", ""))
                        if "반려동물" not in cat_text and "동물병원" not in cat_text:
                            continue
                        category = _category(doc, fallback)
                        found[pid] = PetPlace(
                            place_id=pid,
                            name=str(doc.get("place_name") or ""),
                            category=category,
                            coordinate=Coordinate(float(doc["y"]), float(doc["x"])),
                            address=str(
                                doc.get("road_address_name") or doc.get("address_name") or ""
                            ),
                            url=str(doc.get("place_url") or ""),
                            phone=str(doc.get("phone") or ""),
                        )
        except (httpx.HTTPError, ValueError) as e:
            logger.warning("[KakaoPetPlace] 검색 실패 | %s", e)
            return []
        places = list(found.values())
        self._cache[key] = (time.monotonic(), places)
        return places
