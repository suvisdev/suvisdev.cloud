from __future__ import annotations

from abc import ABC, abstractmethod


class AvatarStorage(ABC):
    """아바타 이미지 저장소 출력 포트(S3).

    프로필 행을 다루는 `ProfileRepository`와 분리한 이유: 저장 매체가 DB가
    아니라 객체 스토리지이고, 조회 시 URL 발급이라는 DB에 없는 동작이 필요하다.
    """

    @abstractmethod
    async def upload(self, user_id: int, data: bytes, *, content_type: str, ext: str) -> str:
        """이미지를 올리고 저장된 객체 key를 돌려준다."""

    @abstractmethod
    def build_url(self, key: str) -> str | None:
        """key로 표시용 URL을 발급한다. 실패하면 None(프로필 조회 자체는 막지 않는다)."""
