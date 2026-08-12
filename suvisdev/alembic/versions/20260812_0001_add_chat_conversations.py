"""add chat_conversations and chat_messages tables (mova)

Claude/Gemini 스타일 대화 스레드 저장용. 기존 `mova.chat`(검색 로그)은
그대로 유지, 새 두 테이블이 사이드바용 스레드 데이터를 담당한다.
익명 사용자는 저장하지 않으므로 `user_id`는 NOT NULL.

Revision ID: 20260812_0001
Revises: 20260811_0003
Create Date: 2026-08-12
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260812_0001"
down_revision: str | None = "20260811_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE chat_conversations (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title VARCHAR(80) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_chat_conversations_user_id ON chat_conversations (user_id)")
    op.execute(
        "CREATE INDEX ix_chat_conversations_updated_at ON chat_conversations (updated_at DESC)"
    )

    op.execute(
        """
        CREATE TABLE chat_messages (
            id SERIAL PRIMARY KEY,
            conversation_id INTEGER NOT NULL REFERENCES chat_conversations(id) ON DELETE CASCADE,
            role VARCHAR(16) NOT NULL,
            content TEXT NOT NULL,
            meta JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_chat_messages_conversation_id ON chat_messages (conversation_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS chat_messages")
    op.execute("DROP TABLE IF EXISTS chat_conversations")
