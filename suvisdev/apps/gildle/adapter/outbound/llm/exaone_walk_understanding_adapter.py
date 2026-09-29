"""산책 요청 이해 — EXAONE 7.8B(Ollama) JSON 모드(2026-09-28, mova 이해 어댑터와 같은 구조).

모델은 슬롯만 채운다. 값 검증·폴백은 domain/services/walk_request.verify, 경로는 A*가 만든다.
"""

from __future__ import annotations

import os

from core.lol.suvisdev_orchestrator import SuvisdevOrchestrator, SuvisdevOrchestratorError
from gildle.app.ports.output.walk_understanding_port import (
    WalkUnderstandingError,
    WalkUnderstandingPort,
)

_DEFAULT_MODEL = "exaone3.5:7.8b"

SYSTEM_PROMPT = """너는 반려견 산책 앱 '길들'의 이해 담당이다. 보호자의 말을 읽고 아래 JSON 한 개만 출력한다. 설명 금지.
{"kind":"loop|route","minutes":숫자 또는 null,"distance_km":숫자 또는 null,"preference":"fast|shade|green|flat|hilly","stops":["동물병원"|"펫샵"|"용품점"|"애견카페"],"destination":"동물병원"|"펫샵"|"용품점"|"애견카페"|null}

- kind: 출발지(집)로 돌아오는 산책이면 loop, 다른 목적지까지 가는 길이면 route. 모르면 loop.
- destination: "○○으로 가는", "○○까지"처럼 목적지가 있으면 그 장소 종류(route). 목적지는 stops에 넣지 않는다. 없으면 null.
- minutes: 산책 시간(분). "한 시간 반"=90. 말하지 않았으면 null.
- distance_km: 산책 거리(km). "2키로"=2, "500미터"=0.5. 말하지 않았으면 null.
- preference: 편하게·평지·노견·무릎 → flat, 언덕·오르막·운동 → hilly, 그늘·더위 → shade, 나무·숲·공원 → green, 빨리·최단·짧게 → fast. 말하지 않았으면 flat.
- stops: 들르고 싶은 곳. 병원·접종 → 동물병원, 사료·간식·용품 → 용품점, 미용·펫샵 → 펫샵, 카페 → 애견카페. 없으면 [].

예) "오늘은 40분 동안 3키로 정도 편하게 걷고 집에 올래" → {"kind":"loop","minutes":40,"distance_km":3,"preference":"flat","stops":[],"destination":null}
예) "운동 좀 되게 언덕 있는 길로 한 시간, 가는 길에 사료 사고 싶어" → {"kind":"loop","minutes":60,"distance_km":null,"preference":"hilly","stops":["용품점"],"destination":null}
예) "강아지 병원으로 가는 최단 경로 알려줘" → {"kind":"route","minutes":null,"distance_km":null,"preference":"fast","stops":[],"destination":"동물병원"}
예) "오늘은 그늘로만 산책하고 싶어" → {"kind":"loop","minutes":null,"distance_km":null,"preference":"shade","stops":[],"destination":null}"""


class ExaoneWalkUnderstandingAdapter(WalkUnderstandingPort):
    def __init__(self, client: SuvisdevOrchestrator | None = None) -> None:
        self._client = client or SuvisdevOrchestrator(
            model=os.getenv("GILDLE_ORCHESTRATOR_MODEL", _DEFAULT_MODEL),
            timeout=float(os.getenv("GILDLE_ORCHESTRATOR_TIMEOUT_S", "15")),
        )

    def understand(self, text: str) -> dict[str, object]:
        try:
            return self._client.understand_json(
                f"[보호자의 말]\n{text[:300]}", system=SYSTEM_PROMPT, num_ctx=2048
            )
        except SuvisdevOrchestratorError as e:
            raise WalkUnderstandingError(e.detail) from e
