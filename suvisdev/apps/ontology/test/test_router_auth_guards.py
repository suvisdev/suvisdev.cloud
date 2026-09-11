"""2026-09-11 리뷰 H4 — 무인증이던 GPU·LLM 엔드포인트 가드 회귀 고정.

face/train·sentinel/detect·genre/classify·sentiment/analyze·semantic/ask는
admin 전용, face/predict는 require_user. 무토큰 요청은 전부 401이어야 한다.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from ontology.adapter.inbound.api.v1.anomaly_detection_router import (  # noqa: E402
    anomaly_detection_router,
)
from ontology.adapter.inbound.api.v1.face_router import face_router  # noqa: E402
from ontology.adapter.inbound.api.v1.image_classifier_router import (  # noqa: E402
    image_classifier_router,
)
from ontology.adapter.inbound.api.v1.semantic_router import semantic_router  # noqa: E402
from ontology.adapter.inbound.api.v1.sentiment_analysis_router import (  # noqa: E402
    sentiment_analysis_router,
)
from ontology.dependencies.anomaly_detection_provider import (  # noqa: E402
    get_anomaly_detection_use_case,
)
from ontology.dependencies.echo_sentiment_provider import (  # noqa: E402
    get_sentiment_analysis_use_case,
)
from ontology.dependencies.face_provider import get_face_use_case  # noqa: E402
from ontology.dependencies.image_classifier_provider import (  # noqa: E402
    get_image_classifier_use_case,
)
from ontology.dependencies.semantic_router_provider import (  # noqa: E402
    get_semantic_router_use_case,
)


def _make_app() -> FastAPI:
    app = FastAPI()
    for r in (
        face_router,
        anomaly_detection_router,
        image_classifier_router,
        sentiment_analysis_router,
        semantic_router,
    ):
        app.include_router(r)
    for dep in (
        get_face_use_case,
        get_anomaly_detection_use_case,
        get_image_classifier_use_case,
        get_sentiment_analysis_use_case,
        get_semantic_router_use_case,
    ):
        app.dependency_overrides[dep] = lambda: MagicMock()
    return app


class RouterAuthGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(_make_app())

    def test_upload_endpoints_reject_anonymous(self) -> None:
        files = {"file": ("a.jpg", b"x", "image/jpeg")}
        for path in ("/face/predict", "/sentinel/detect", "/genre/classify"):
            with self.subTest(path=path):
                self.assertEqual(self.client.post(path, files=files).status_code, 401)

    def test_train_rejects_anonymous(self) -> None:
        self.assertEqual(self.client.post("/face/train").status_code, 401)

    def test_train_caps_epochs(self) -> None:
        """admin이어도 상한(100) 초과 epochs는 422 — GPU 무기한 점유 방지."""
        from shared.security.require_admin import AdminPrincipal, require_admin

        app = _make_app()
        app.dependency_overrides[require_admin] = lambda: AdminPrincipal(
            user_id=1, username="admin"
        )
        res = TestClient(app).post("/face/train?epochs=100000")
        self.assertEqual(res.status_code, 422)

    def test_sentiment_and_semantic_reject_anonymous(self) -> None:
        self.assertEqual(
            self.client.post("/sentiment/analyze", json={"text": "좋아요"}).status_code, 401
        )
        self.assertEqual(
            self.client.post("/semantic/ask", json={"question": "안녕"}).status_code, 401
        )


if __name__ == "__main__":
    unittest.main()
