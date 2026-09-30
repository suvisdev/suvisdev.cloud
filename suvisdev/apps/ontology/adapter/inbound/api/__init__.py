"""ontology inbound API 라우터 집약.

라우터 import는 무겁다 — vision·sentiment 라우터가 torch/opencv를 끌어온다. 예전엔 이
패키지를 import하기만 해도(하위 모듈 import도 부모 패키지를 먼저 로드한다) torch가
통째로 올라와, 무거운 것과 무관한 테스트까지 느려지고 HF 오프라인 환경에서 hang처럼
멈췄다(WORK_LOG 09-29). 그래서 조립을 **지연**시킨다(PEP 562 `__getattr__`) — `import
...api`만으로는 아무 무거운 모듈도 로드되지 않고, main.py(Composition Root)가 실제로
각 라우터를 꺼낼 때만 해당 하위 모듈을 import한다. 한 번 만든 라우터는 모듈 전역에
캐시해 재조립하지 않는다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import APIRouter

__all__ = ["nlp_router", "ontology_router", "portfolio_router", "vision_router"]


def _build_vision_router() -> APIRouter:
    from fastapi import APIRouter

    from ontology.adapter.inbound.api.v1.anomaly_detection_router import anomaly_detection_router
    from ontology.adapter.inbound.api.v1.face_router import face_router
    from ontology.adapter.inbound.api.v1.image_classifier_router import image_classifier_router
    from ontology.adapter.inbound.api.v1.vision_router import vision_introduce_router

    router = APIRouter(prefix="/vision", tags=["vision"])
    router.include_router(vision_introduce_router)
    router.include_router(face_router)
    router.include_router(image_classifier_router)
    router.include_router(anomaly_detection_router)
    return router


def _build_ontology_router() -> APIRouter:
    from fastapi import APIRouter

    from ontology.adapter.inbound.api.v1.harvester_router import harvester_router
    from ontology.adapter.inbound.api.v1.semantic_router import semantic_router

    router = APIRouter(prefix="/ontology", tags=["ontology"])
    router.include_router(semantic_router)
    router.include_router(harvester_router)
    return router


def _build_nlp_router() -> APIRouter:
    from fastapi import APIRouter

    from ontology.adapter.inbound.api.v1.sentiment_analysis_router import sentiment_analysis_router

    router = APIRouter(prefix="/nlp", tags=["nlp"])
    router.include_router(sentiment_analysis_router)
    return router


def _build_portfolio_router() -> APIRouter:
    from fastapi import APIRouter

    from ontology.adapter.inbound.api.v1.portfolio_chat_router import portfolio_chat_router

    router = APIRouter(prefix="/portfolio", tags=["portfolio"])
    router.include_router(portfolio_chat_router)
    return router


_BUILDERS = {
    "vision_router": _build_vision_router,
    "ontology_router": _build_ontology_router,
    "nlp_router": _build_nlp_router,
    "portfolio_router": _build_portfolio_router,
}


def __getattr__(name: str) -> APIRouter:
    builder = _BUILDERS.get(name)
    if builder is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    router = builder()
    globals()[name] = router  # 캐시 — 다음 접근은 __getattr__을 거치지 않는다
    return router
