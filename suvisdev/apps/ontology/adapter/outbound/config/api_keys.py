"""API 키는 여기서만 환경변수로 읽는다 — 코드·yaml·로그 어디에도 값 자체를 남기지 않는다.

키가 없으면 그 어댑터의 search() 호출 시점에 여기서 예외를 던진다(어댑터 생성자가 아니라
사용 시점) — SITE_REGISTRY에는 그대로 남아 `sites` 커맨드에 노출되고, 다른 사이트는
이 예외와 무관하게 정상 동작한다.
"""

from __future__ import annotations

import os


class MissingApiKeyError(Exception):
    def __init__(self, env_var: str, site_id: str) -> None:
        self.env_var = env_var
        self.site_id = site_id
        super().__init__(f"{env_var} 환경변수가 없어 {site_id} 어댑터를 사용할 수 없습니다")


def get_tmdb_api_key() -> str:
    key = os.getenv("TMDB_API_KEY")
    if not key:
        raise MissingApiKeyError("TMDB_API_KEY", "tmdb")
    return key


def get_kobis_api_key() -> str:
    key = os.getenv("KOBIS_API_KEY")
    if not key:
        raise MissingApiKeyError("KOBIS_API_KEY", "kobis")
    return key
