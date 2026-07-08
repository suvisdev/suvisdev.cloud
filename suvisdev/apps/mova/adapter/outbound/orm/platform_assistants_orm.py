"""Mova AI 채팅 상대(페르소나) — `assistants`."""

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from mova.adapter.outbound.orm.base_orm import MovaModel


class MovaAssistant(MovaModel):
    """유저가 대화하는 AI 컨시어지 등. 영화 `actors` 와 별도."""

    __tablename__ = "assistants"

    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    avatar_url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    default_model: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="flash15",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
