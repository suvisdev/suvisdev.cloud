"""어시스턴트 DTO."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mova.adapter.inbound.api.schemas.platform_assistants_schema import (
        AssistantListSchema,
        AssistantSchema,
    )


@dataclass(frozen=True)
class AssistantDto:
    id: int
    slug: str
    display_name: str
    avatar_url: str
    system_prompt: str
    default_model: str
    is_active: bool

    @classmethod
    def from_orm(cls, row: Any) -> AssistantDto:
        return cls(
            id=row.id,
            slug=row.slug,
            display_name=row.display_name,
            avatar_url=row.avatar_url or "",
            system_prompt=row.system_prompt or "",
            default_model=row.default_model or "flash15",
            is_active=bool(row.is_active),
        )

    def to_schema(self) -> AssistantSchema:
        from mova.adapter.inbound.api.schemas.platform_assistants_schema import AssistantSchema

        return AssistantSchema(
            id=self.id,
            slug=self.slug,
            display_name=self.display_name,
            avatar_url=self.avatar_url,
            system_prompt=self.system_prompt,
            default_model=self.default_model,
            is_active=self.is_active,
        )


@dataclass(frozen=True)
class AssistantListDto:
    items: list[AssistantDto]

    def to_schema(self) -> AssistantListSchema:
        from mova.adapter.inbound.api.schemas.platform_assistants_schema import AssistantListSchema

        return AssistantListSchema(items=[item.to_schema() for item in self.items])
