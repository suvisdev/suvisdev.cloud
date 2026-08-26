"""AI 리뷰 writer — mova DB에 직접 SQL로 접근한다.

mova ORM을 import하면 Hub→Spoke 의존이 되므로, text() SQL로 reviews/movies/users
테이블에 접근한다. core.matrix의 get_mova_session_factory()는 Hub에서 import 가능.
"""

from __future__ import annotations

import logging
import secrets

import bcrypt
from sqlalchemy import text

from core.matrix.grid_oracle_database_manager import get_mova_session_factory
from ontology.app.ports.output.ai_review_writer_port import AiReviewWriterPort

logger = logging.getLogger(__name__)

_AI_REVIEWER_USERNAME = "ai_reviewer"
_AI_REVIEWER_NICKNAME = "AI 평론가"
_AI_REVIEWER_EMAIL = "ai_reviewer@suvisdev.cloud"


def _locked_password_hash() -> str:
    """어떤 입력으로도 로그인할 수 없는 비밀번호 해시.

    viewer의 _verify_password에 평문·sha256 비교 폴백이 있어, 소스에 노출된
    고정 문자열을 넣으면 그 문자열 자체로 로그인이 된다. 무작위 비밀번호의
    bcrypt 해시를 저장하면 원문을 아무도 모르므로 어떤 경로로도 통과 불가.
    """
    random_password = secrets.token_hex(32).encode("utf-8")
    return bcrypt.hashpw(random_password, bcrypt.gensalt()).decode("utf-8")


class AiReviewPgAdapter(AiReviewWriterPort):
    async def find_movie_id_by_title(self, title: str) -> int | None:
        factory = get_mova_session_factory()
        async with factory() as session:
            result = await session.execute(
                text("SELECT id FROM movies WHERE LOWER(title) = LOWER(:title) LIMIT 1"),
                {"title": title},
            )
            row = result.scalar_one_or_none()
            return int(row) if row is not None else None

    async def ensure_ai_reviewer_user(self) -> int:
        factory = get_mova_session_factory()
        async with factory() as session:
            result = await session.execute(
                text("SELECT id FROM users WHERE username = :username"),
                {"username": _AI_REVIEWER_USERNAME},
            )
            existing = result.scalar_one_or_none()
            if existing is not None:
                return int(existing)

            group_result = await session.execute(
                text("SELECT id FROM groups WHERE code = 'user' LIMIT 1"),
            )
            group_id = group_result.scalar_one_or_none()
            if group_id is None:
                raise RuntimeError(
                    "groups 테이블에 'user' 그룹이 없습니다. seed를 먼저 실행하세요."
                )

            insert_result = await session.execute(
                text(
                    "INSERT INTO users (group_id, username, password_hash, nickname, email, gender, preferred_genres) "
                    "VALUES (:group_id, :username, :password_hash, :nickname, :email, 'undisclosed', '[]'::jsonb) "
                    "RETURNING id"
                ),
                {
                    "group_id": int(group_id),
                    "username": _AI_REVIEWER_USERNAME,
                    "password_hash": _locked_password_hash(),
                    "nickname": _AI_REVIEWER_NICKNAME,
                    "email": _AI_REVIEWER_EMAIL,
                },
            )
            user_id = insert_result.scalar_one()
            await session.commit()
            logger.info("[AiReviewPgAdapter] ai_reviewer 계정 생성 | user_id=%d", user_id)
            return int(user_id)

    async def has_ai_review(self, user_id: int, movie_id: int) -> bool:
        factory = get_mova_session_factory()
        async with factory() as session:
            result = await session.execute(
                text(
                    "SELECT 1 FROM reviews WHERE user_id = :user_id AND movie_id = :movie_id LIMIT 1"
                ),
                {"user_id": user_id, "movie_id": movie_id},
            )
            return result.scalar_one_or_none() is not None

    async def save_review(self, *, user_id: int, movie_id: int, rating: float, body: str) -> int:
        clamped_rating = max(1.0, min(5.0, round(rating * 2) / 2))
        factory = get_mova_session_factory()
        async with factory() as session:
            result = await session.execute(
                text(
                    "INSERT INTO reviews (user_id, movie_id, rating, body) "
                    "VALUES (:user_id, :movie_id, :rating, :body) "
                    "RETURNING id"
                ),
                {
                    "user_id": user_id,
                    "movie_id": movie_id,
                    "rating": clamped_rating,
                    "body": body,
                },
            )
            review_id = result.scalar_one()
            await session.commit()
            return int(review_id)
