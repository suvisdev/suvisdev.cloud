"""2026-09-11 리뷰 H4 — titanic 변이·학습 엔드포인트 admin 가드 회귀 고정.

james/upload(무인증 DB 쓰기 + 무제한 read), rose/train·predict(무인증 학습·
모델 파일 덮어쓰기)를 require_admin으로 잠근 것을 고정한다.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from titanic.adapter.inbound.api.v1.crew_james_director_router import james_director_router
from titanic.adapter.inbound.api.v1.passenger_rose_model_router import rose_model_router
from titanic.dependencies.crew_james_director_provider import get_james_director_use_case
from titanic.dependencies.passenger_rose_model_provider import get_rose_model_use_case


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(james_director_router)
    app.include_router(rose_model_router)
    app.dependency_overrides[get_james_director_use_case] = lambda: MagicMock()
    app.dependency_overrides[get_rose_model_use_case] = lambda: MagicMock()
    return app


class TitanicAuthGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(_make_app())

    def test_upload_rejects_anonymous(self) -> None:
        res = self.client.post("/james/upload", files={"file": ("t.csv", b"a,b\n1,2", "text/csv")})
        self.assertEqual(res.status_code, 401)

    def test_rose_train_and_predict_reject_anonymous(self) -> None:
        self.assertEqual(self.client.post("/rose/train", json={}).status_code, 401)
        self.assertEqual(self.client.post("/rose/predict", json={}).status_code, 401)


if __name__ == "__main__":
    unittest.main()
