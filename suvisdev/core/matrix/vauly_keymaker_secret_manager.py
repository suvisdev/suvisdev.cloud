"""API 키·외부 서비스 설정을 한 객체에서 관리한다.

계약(contract): 이 모듈을 임포트하면 모듈 로드 시점의 싱글턴(`keymaker = Keymaker()`)이
`suvisdev/.env`를 `load_dotenv(override=True)`로 읽어 `os.environ`에 채운다.
이 self-load는 **버그가 아니라 기능**이다 — `main.py`(FastAPI 진입점)를 거치지 않고
Keymaker를 직접 임포트하는 `scripts/`(예: harvester_cli, 학습 스크립트)가 이 자동
로드에 의존한다. 진입점 단일화를 이유로 **제거하지 말 것.** (컨테이너에서는 .env
파일이 이미지에 없어 load_dotenv가 no-op이고 env는 compose env_file로 주입된다.)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

ModelKey = Literal["flash", "flash15", "pro"]

# 프론트 선택값 → Gemini 모델 ID (list_models 기준, generateContent 지원)
GEMINI_MODEL_MAP: dict[ModelKey, str] = {
    "flash": "gemini-3.1-flash-lite",
    "flash15": "gemini-3.1-flash-lite",
    "pro": "gemini-3.1-pro-preview",
}

DEFAULT_MODEL_KEY: ModelKey = "flash15"

# v1beta에서 404 나는 구형 ID → 권장 모델로 대체
_LEGACY_MODEL_ALIASES: dict[str, str] = {
    "gemini-1.5-flash": "gemini-3.1-flash-lite",
    "gemini-1.5-flash-8b": "gemini-3.1-flash-lite",
    "gemini-1.5-pro": "gemini-3.1-pro-preview",
    "gemini-2.0-flash": "gemini-3.1-flash-lite",
    "gemini-2.5-flash": "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite": "gemini-3.1-flash-lite",
    "gemini-2.5-pro": "gemini-3.1-pro-preview",
}


def _normalize_model_id(model_id: str) -> str:
    mid = model_id.strip()
    if not mid:
        return GEMINI_MODEL_MAP[DEFAULT_MODEL_KEY]
    if mid.startswith("models/"):
        mid = mid.removeprefix("models/")
    return _LEGACY_MODEL_ALIASES.get(mid, mid)


def _default_env_path() -> Path:
    return Path(__file__).resolve().parents[2] / ".env"


class Keymaker:
    """`suvisdev/.env`를 로드하고, Gemini 등 백엔드가 쓰는 자격 증명·클라이언트를 제공한다."""

    def __init__(self, *, env_path: Path | None = None) -> None:
        self.env_path = Path(env_path) if env_path else _default_env_path()
        load_dotenv(self.env_path, override=True)

        self.gemini_api_key: str = (os.getenv("GEMINI_API_KEY") or "").strip()
        self.tmdb_api_key: str = (os.getenv("TMDB_API_KEY") or "").strip()
        self.kofic_api_key: str = (os.getenv("KOFIC_API_KEY") or "").strip()

        # AWS S3 — Tank(aws_tank_s3_manager)가 region/bucket을 읽어 쓴다.
        # aws_access_key_id/secret은 vestigial(현재 아무도 안 읽음): Tank가 boto3
        # 기본 자격증명 체인을 쓰고, 그 체인은 .env가 os.environ에 실은 AWS_* env를
        # 직접 집는다. 속성은 향후 참조/디버깅용으로 남겨둔다.
        self.aws_access_key_id: str = (os.getenv("AWS_ACCESS_KEY_ID") or "").strip()
        self.aws_secret_access_key: str = (os.getenv("AWS_SECRET_ACCESS_KEY") or "").strip()
        self.aws_region: str = (os.getenv("AWS_REGION") or "ap-northeast-2").strip()  # 서울
        self.vision_s3_bucket: str = (os.getenv("VISION_S3_BUCKET") or "").strip()

        self._genai_client: object | None = None

        if self.gemini_api_key:
            from google import genai

            self._genai_client = genai.Client(api_key=self.gemini_api_key)

    def resolve_model_id(self, model_key: str | None) -> str:
        """프론트 `model` 키 또는 .env `GEMINI_MODEL` → 실제 모델 ID."""
        if model_key and model_key in GEMINI_MODEL_MAP:
            return GEMINI_MODEL_MAP[model_key]  # type: ignore[index]
        env_id = (os.getenv("GEMINI_MODEL") or "").strip()
        if env_id:
            return _normalize_model_id(env_id)
        return GEMINI_MODEL_MAP[DEFAULT_MODEL_KEY]

    @property
    def genai_client(self):
        """google.genai.Client 인스턴스. API 키 미설정 시 None."""
        return self._genai_client

    def get_gemini_model(self, model_key: str | None = None):
        """하위 호환 — genai_client + resolve_model_id 조합을 권장."""
        if not self.gemini_api_key:
            return None
        return self.resolve_model_id(model_key)

    @property
    def gemini_model(self):
        return self.get_gemini_model(None)

    @property
    def gemini_ready(self) -> bool:
        return bool(self.gemini_api_key)

    def is_gemini_ready(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def database_url(self) -> str:
        return (os.getenv("DATABASE_URL") or "").strip()


keymaker = Keymaker()


def get_keymaker() -> Keymaker:
    return keymaker
