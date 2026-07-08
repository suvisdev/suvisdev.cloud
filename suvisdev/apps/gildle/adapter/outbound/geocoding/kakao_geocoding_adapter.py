from __future__ import annotations

import logging
import os

import httpx

from gildle.app.ports.output.geocoding_port import GeocodingPort
from gildle.domain.value_objects.coordinate import Coordinate

logger = logging.getLogger(__name__)

_KAKAO_ADDRESS_URL = "https://dapi.kakao.com/v2/local/search/address.json"


class KakaoGeocodingAdapter(GeocodingPort):
    """GeocodingPort의 카카오 로컬 API 구현체(좌표 결측 보완용 fallback).

    API Key는 `KAKAO_API_KEY` 환경변수에서 읽는다.
    오류/결과없음은 모두 이 경계 안에서 흡수하고 None을 돌려준다 — Use Case는 깨끗한 값만 본다.
    """

    def __init__(self, timeout_seconds: float = 5.0) -> None:
        self._timeout = timeout_seconds

    def geocode(self, address: str) -> Coordinate | None:
        api_key = os.getenv("KAKAO_API_KEY")
        if not api_key:
            logger.warning("KAKAO_API_KEY 미설정 — geocoding 생략")
            return None

        try:
            response = httpx.get(
                _KAKAO_ADDRESS_URL,
                headers={"Authorization": f"KakaoAK {api_key}"},
                params={"query": address},
                timeout=self._timeout,
            )
            response.raise_for_status()
            documents = response.json().get("documents", [])
            if not documents:
                return None
            document = documents[0]
            return Coordinate(
                latitude=float(document["y"]),
                longitude=float(document["x"]),
            )
        except Exception:  # noqa: BLE001 - 경계에서 모든 외부 오류를 None으로 흡수
            logger.exception("카카오 geocoding 실패: %s", address)
            return None
