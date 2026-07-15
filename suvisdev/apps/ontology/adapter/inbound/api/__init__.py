from fastapi import APIRouter

from ontology.adapter.inbound.api.v1.face_router import face_router
from ontology.adapter.inbound.api.v1.semantic_router import semantic_router
from ontology.adapter.inbound.api.v1.vision_router import vision_introduce_router

# 앱 라우터 집약 — main.py(Composition Root)에서 이 vision_router만 include한다.
vision_router = APIRouter(prefix="/vision", tags=["vision"])
vision_router.include_router(vision_introduce_router)
vision_router.include_router(face_router)

# 시맨틱 게이트웨이 라우터 — vision과 성격이 달라 별도로 export한다.
ontology_router = APIRouter(prefix="/ontology", tags=["ontology"])
ontology_router.include_router(semantic_router)
