"""API 키·외부 서비스 설정을 한 객체에서 관리한다."""

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
        self.openweather_api_key: str = (
            os.getenv("OPENWEATHERMAP_API_KEY") or os.getenv("OPENWEATHER_API_KEY") or ""
        ).strip()
        self.openweather_city: str = (os.getenv("OPENWEATHER_CITY") or "Seoul").strip()
        self.tmdb_api_key: str = (os.getenv("TMDB_API_KEY") or "").strip()
        self.kofic_api_key: str = (os.getenv("KOFIC_API_KEY") or "").strip()
        self._gemini_models: dict[str, object] = {}

        if self.gemini_api_key:
            import google.generativeai as genai

            genai.configure(api_key=self.gemini_api_key)

    def resolve_model_id(self, model_key: str | None) -> str:
        """프론트 `model` 키 또는 .env `GEMINI_MODEL` → 실제 모델 ID."""
        if model_key and model_key in GEMINI_MODEL_MAP:
            return GEMINI_MODEL_MAP[model_key]  # type: ignore[index]
        env_id = (os.getenv("GEMINI_MODEL") or "").strip()
        if env_id:
            return _normalize_model_id(env_id)
        return GEMINI_MODEL_MAP[DEFAULT_MODEL_KEY]

    def get_gemini_model(self, model_key: str | None = None):
        """키가 없으면 `None`. `model_key`에 맞는 `GenerativeModel`(캐시)을 반환."""
        if not self.gemini_api_key:
            return None

        import google.generativeai as genai

        model_id = self.resolve_model_id(model_key)
        if model_id not in self._gemini_models:
            self._gemini_models[model_id] = genai.GenerativeModel(model_id)
        return self._gemini_models[model_id]

    @property
    def gemini_model(self):
        return self.get_gemini_model(None)

    @property
    def gemini_ready(self) -> bool:
        return bool(self.gemini_api_key)

    def is_gemini_ready(self) -> bool:
        return bool(self.gemini_api_key)

    def is_openweather_ready(self) -> bool:
        return bool(self.openweather_api_key)

    def reload_openweather_env(self) -> None:
        """`.env` 변경 후에도 날씨 키를 다시 읽는다."""
        load_dotenv(self.env_path, override=True)
        self.openweather_api_key = (
            os.getenv("OPENWEATHERMAP_API_KEY") or os.getenv("OPENWEATHER_API_KEY") or ""
        ).strip()
        self.openweather_city = (os.getenv("OPENWEATHER_CITY") or "Seoul").strip()
        self.tmdb_api_key = (os.getenv("TMDB_API_KEY") or "").strip()
        self.kofic_api_key = (os.getenv("KOFIC_API_KEY") or "").strip()

    @property
    def database_url(self) -> str:
        return (os.getenv("DATABASE_URL") or "").strip()


keymaker = Keymaker()


def get_keymaker() -> Keymaker:
    return keymaker
